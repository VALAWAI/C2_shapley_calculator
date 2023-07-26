from copy import deepcopy
from flask import Flask, Request, request
from itertools import combinations
from math import factorial
from pathos.multiprocessing import cpu_count, ProcessPool
from traceback import format_exc

from typing import Any, Callable, Type


def evaluate_path(
    model_cls: Type,
    model_args: list[Any],
    model_kwargs: dict[str, Any],
    norms: dict[str, dict[str, Any]],
    value: Callable[[object], float],
    path_length: int
) -> float:
    """Evaluate the outcome of a path in terms of a value.

    Parameters
    ----------
    model_cls : Type[...]
        Class of the model.
    model_args : list[Any]
        Model initilization arguments.
    model_kwargs : dict[str, Any]
        Model initialization keyword arguments.
    norms : dict[str, dict[str, Any]]
        The set of norms governing the evolution of the model.
    value : Callable[[object], float]
        The value semantics function that evaluates the final state of a path.
    path_length : int
        The number of steps in the path to evaluate.

    Returns
    -------
    float
    """
    mdl = model_cls(*model_args, **model_kwargs)
    for _ in range(path_length):
        mdl.step(norms)
    return value(mdl)


def alignment(
    model_cls: Type,
    model_args: list[Any],
    model_kwargs: dict[str, Any],
    norms: dict[str, dict[str, Any]],
    value: Callable[[object], float],
    path_length: int,
    path_sample: int,
    pool: ProcessPool
) -> float:
    """Compute the alignment from a sample of paths.

    This function uses a ``pathos.multiprocessing.ProcessPool`` already
    initialized to speed up the sampling.

    Parameters
    ----------
    model_cls : Type[Model]
        Class of the model.
    model_args : list[Any]
        Model initilization arguments.
    model_kwargs : dict[str, Any]
        Model initialization keyword arguments.
    norms : dict[str, dict[str, Any]]
        The set of norms governing the evolution of the model.
    value : Callable[[object], float]
        The value semantics function that evaluates the final state of a path.
    path_length : int
        The number of steps in the path to evaluate.
    path_sample : int
        The number of paths to sample.
    pool : ProcessPool
        A ``pathos.multiprocessing.ProcessPool`` to parallelize sampling.

    Returns
    -------
    float
    """
    args = [
        [model_cls] * path_sample,
        [model_args] * path_sample,
        [model_kwargs] * path_sample,
        [norms] * path_sample,
        [value] * path_sample,
        [path_length] * path_sample
    ]
    pool.restart()
    algn = 0.
    for res in pool.map(evaluate_path, *args):
        algn += res
    pool.close()
    pool.terminate()
    return algn / path_sample
    

def shapley_value(
    model_cls: Type,
    model_args: list[Any],
    model_kwargs: dict[str, Any],
    baseline_norms: dict[str, dict[str, Any]],
    normative_system: dict[str, dict[str, Any]],
    norm: str,
    value: Callable[[object], float],
    path_length: int = 10,
    path_sample: int = 100
) -> float:
    """Compute the Shapley value of a norm in a normative system.

    This calculator computes the Shapley value of individual norms in a
    normative system with respect to some value. For a complete
    formalization of the Shapley values of norms in a normative system, see
    [1]_.

    Parameters
    ----------
    model_cls : Type[...]
        Class of the model.
    model_args : list[Any]
        Model initilization arguments.
    model_kwargs : dict[str, Any]
        Model initialization keyword arguments.
    baseline_norms : dict[str, dict[str, Any]]
        The baseline norms causing no evolution of the ABM.
    normative_system : dict[str, dict[str, Any]]
        The complete normative system, as a mapping of norm IDs (the keys)
        to a dictionary of its normative parameters.
    norm : str
        The ID of the norm whose Shapley value is computed.
    value : Callable[[object], float]
        The value with respect to which the Shapley value is computed. It is
        passed as a function taking as input a model instance and returning
        the evaluation of the value semantics function given the state of
        the model.
    path_length : int, optional
        The length of the evolution path used to compute the alignment, by
        default 10.
    path_sample : int, optional
        The number of paths to sample when computing the alignment, by
        default 100.

    Returns
    -------
    float
        The Shapley value of ``norm`` in ``normative_system`` with respect
        to ``value``.

    References
    ----------
    .. [1] Montes, N., & Sierra, C. (2022). Synthesis and properties of
        optimally value-aligned normative systems. Journal of Artificial
        Intelligence Research, 74, 1739–1774.
        https://doi.org/10.1613/jair.1.13487
    """
    # check that norms match
    assert normative_system.keys() == baseline_norms.keys(), \
        "normative system must have identical norms to the baseline normative system"
    for norm_id, params in normative_system.items():
        assert params.keys() == baseline_norms[norm_id].keys(), \
        f"norm {norm_id} does not have the same params in the normative \
            system and in the baseline normative system"
        
    # prepare list of norms id's for the subsets of norms
    all_norms_ids = list(baseline_norms.keys())
    all_norms_except_n = deepcopy(all_norms_ids)
    all_norms_except_n.remove(norm)

    N = len(all_norms_ids)
    combo_max_size = len(all_norms_except_n)
    shapley = 0.

    # prepare pool for parallelization
    num_nodes = cpu_count()
    if path_sample <= num_nodes:
        num_nodes = path_sample
    pool = ProcessPool(nodes=num_nodes)

    for N_prime in range(combo_max_size + 1):
        factor = factorial(N_prime) * factorial(N - N_prime - 1) / factorial(N)

        for norms_prime in combinations(all_norms_except_n, N_prime):
            normative_system_prime = {}
            for n_id in all_norms_ids:
                if n_id in norms_prime:
                    normative_system_prime[n_id] = normative_system[n_id]
                else:
                    normative_system_prime[n_id] = baseline_norms[n_id]

            normative_system_prime_union = deepcopy(normative_system_prime)
            normative_system_prime_union[norm] = normative_system[norm]

            algn1 = alignment(
                model_cls, model_args, model_kwargs,
                normative_system_prime_union, value, path_length,
                path_sample, pool
            )
            algn2 = alignment(
                model_cls, model_args, model_kwargs,
                normative_system_prime, value, path_length, 
                path_sample, pool
            )

            shapley += factor*(algn1 - algn2)

    pool.terminate()
    return shapley


def create_app(
    model_cls: Type,
    model_args: list[Any],
    model_kwargs: dict[str, Any],
    value: Callable[[object], float]
) -> Flask:
    """Create a Flask app that computes the Shapley value.

    This C2 component of the VALAWAI architecture computes the Shapley value of
    an individual norm (within a normative system) with respect to a value [1]_.

    Parameters
    ----------
    model_cls : Type[...]
        Class of the model.
    model_args : list[Any]
        Model initilization arguments.
    model_kwargs : dict[str, Any]
        Model initilization keyword arguments.
    value : Callable[[object], float]
        The value with respect to which the Shapley value is computed. It is
        passed as a function taking as input a model instance and returning
        the evaluation of the value semantics function given the state of
        the model.

    Returns
    -------
    Flask
        A Flask application that can process GET /shapley requests.

    References
    ----------
    .. [1] Montes, N., & Sierra, C. (2022). Synthesis and properties of optimally
        value-aligned normative systems. Journal of Artificial Intelligence
        Research, 74, 1739–1774. https://doi.org/10.1613/jair.1. 13487
    """
    __EXPECTED_TYPES = {
        'baseline_norms': dict, 'normative_system': dict, 'norm': str,
        'path_length': int, 'path_sample': int
    }
    
    app = Flask(__name__)

    def __check_request(request: Request):
        if not request.is_json:
            return {"error": "Request must be JSON"}, 415
        input_data = request.get_json()
        if not isinstance(input_data, dict):
            return {"error": f"Params must be passed as a dict"}, 400
        return input_data


    @app.get('/shapley')
    def get_shapley():
        input_data = __check_request(request)

        __NEED_KEYS = ['baseline_norms', 'normative_system', 'norm']
        __OPT_KEYS = ['path_length', 'path_sample']

        # check that the input data has all the necessary keys and they are the
        # correct type
        for k in __NEED_KEYS:
            if not k in input_data.keys():
                return {"error": f"missing necessary param {k}"}, 400
        for k in input_data.keys():
            if not isinstance(input_data[k], __EXPECTED_TYPES[k]):
                return {"error": f"type of param {k} must be {__EXPECTED_TYPES[k]}"}, 400

        # get optional arguments path_length and path_sample
        kwargs = {}
        for k in __OPT_KEYS:
            try:
                kwargs[k] = input_data[k]
            except KeyError:
                continue

        # compute and return
        try:
            shap = shapley_value(
                model_cls,
                model_args,
                model_kwargs,
                input_data['baseline_norms'],
                input_data['normative_system'],
                input_data['norm'],
                value,
                **kwargs
            )
            return {'shapley': shap}, 200
        except Exception:
            return {"error": format_exc()}, 400
        
    return app

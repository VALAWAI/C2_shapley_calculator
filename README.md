# C2 Alignment Calculator

The Alignment Calculator is a C2 VALAWAI component that computes the alignment
if a set of norms or (*normative system*) with respect to a value of interest
using simulation and sampling.

This component provides the functionality to compute the Shapley value of an
individual norm $n_i$ within a normative system $N$ (where $n_i \in N$), with
respect to a given value $v$. Given a normative system $N$ and a value $v$, it
is possible to quantify the degree of alignment $\mathsf{Algn}_{N,v}$ that the
norms in $N$ have with respect to value $v$ (see the [Alignment Calculator
component](https://github.com/VALAWAI/C2_alignment_calculator)). The Shapley
value $\phi_i(v)$ of norm $n_i \in N$ quantifies the contribution that the
    specific norm $n_i$ makes to that alignment. It is defined as:
    
$$
    \phi_{i}(v) = \sum\limits_{N'\subseteq N\setminus \{n_i\}}
    \frac{|N'|!\left(|N|-|N'|-1\right)!}{|N|!} \cdot \left(
\mathsf{Algn}_{N'\cup \{n_i\}, v} - \mathsf{Algn}_{N', v} \right)
$$

where the summation is taken over all the subsets of $N$
where $n_i$ is absent, $N \setminus \{n_i\}$. In general, given a normative
system $N$ and a set of norm $\{n_j, n_k, ...\} \subseteq N$, the removal of
$\{n_j, n_k, ...\}$ from $N$ is represented by a normative system $N' = N
\setminus \{n_j, n_k, ...\}$ where the values of the normative parameters tied
to $\{n_j, n_k, ...\}$ are substituted by their *baseline* quantities.
These baseline normative parameters are drawn from a *baseline normative
system* $N_{bsl}$. This baseline normative system has the same norms as $N$,
tied to the same normative parameters, but the values that these baseline
normative parameters are selected in such a way that, when it is implemented on
the model, it does not change its current state.

# Summary

 - Type: C2
 - Name: Shapley Calculator
 - Version: 1.0.0 (September 27, 2023)
 - API: [1.0.0 (February 3, 2023)](https://editor-next.swagger.io/?url=https://raw.githubusercontent.com/VALAWAI/C0_voice_to_text/main/component-api.yml)
 - VALAWAI API: [0.1.0 (September 18, 2023)](https://editor-next.swagger.io/?url=https://raw.githubusercontent.com/VALAWAI/MOV/main/valawai-api.yml)
 - Developed by: IIIA-CSIC
 - License: [MIT](LICENSE)

# Usage

A Shapley Calculator is initialized similarly to the [Alignment
Calculator](https://github.com/VALAWAI/C2_alignment_calculator), by providing
(i) a representation of the model or system being examined (i.e. the entity upon
which norms apply to), and (ii) the semantics function $f_v$ of the value of
interest $v$ whose alignment is computed by the component. The reader is
directed to the instruction of the Alignment Calculator to understand how to
define (i) and (ii). You can use the `template.py` script as a blueprint for
developing the Shapley Calculator with your own model and values.

The Shapley Calculator component is implemented as a
[Flask](https://flask.palletsprojects.com/en/2.3.x/) application. To initialize
it, use the `create_app` function:

```python
from app import create_app

app = create_app(
    YourModel,                      # your model class
    [...],                          # your model initialization arguments
    {...},                          # your model initialization keyword arguments
    baseline_norms,                 # your baseline norms dictionary
    norms,                          # your norms dictionary
    your_value_semantics_function,  # your value semantics function
    # path_length=10,               # change if needed, default is 10
    # path_sample=500               # change if needed, default is 500
)
```

This component communicates through the following HTTP requests:

* Data messages:

    - GET `/shapley` -d norm_id

* Control messages:

    - PATCH `/bsl_norms` changes the baseline normative system
    - PATCH `/norms` changes the normative system
    - PATCH `/path_length` changes the length of the paths used to compute the
      alignment
    - PATH `/path_sample` changes the number of paths sampled to compute the
      alignment

# Deployment

Clone this repository and develop your model and value semantics functions
following the blueprint in `template.py`:

```bash
$ git clone https://github.com/VALAWAI/C2_shapley_calculator.git
```

Build your Docker image in your directory of the component repository:

```bash
$ cd /path/to/c2_shapley_calculator
$ docker build -t c2_shapley_calculator .
```

Run a Docker container with your C2 Shapley Calculator:

```bash
$ docker run --rm -d \
  --network valawai \
  --name c2_shapley_calculator \
  --mount type=bind,src="$(pwd)",target=/app \
  -p 5432:5000 \
  -e MODEL=my_model \
  c2_shapley_calculator
```

The environment variable `MODEL` refers to the script where you have defined
your model (do not include the .py extension).

Once the container is up and running, use `curl` to communicate with the
component:

```bash
$ curl -X GET http://localhost:5432/algn -d pay
{
  "shapley": 0.5502168612232454
}
```

```bash
$ curl -X PATCH http://localhost:5432/path_sample -d 200
{}
```

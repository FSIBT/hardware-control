[![read-the-docs](https://readthedocs.org/projects/hardware-control/badge/?style=flat)](https://readthedocs.org/projects/hardware-control/)
[![PyPI version](https://badge.fury.io/py/hardware-control.svg)](https://badge.fury.io/py/hardware-control)
[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white)](https://github.com/pre-commit/pre-commit)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![DOI](https://joss.theoj.org/papers/10.21105/joss.02688/status.svg)](https://doi.org/10.21105/joss.02688)

## What is this repository for?

The goal is to provide reusable code for hardware control using python and Qt.

Documentation can be found at [Read the Docs](https://readthedocs.org/projects/hardware-control/).

## How do I get set up?

The easiest way is to pip install the software:

    pip install hardware-control

## Examples

If you want to have a quick look at some basic functionality, you can
run the demos in the example directory. If you have the same hardware
that is used in the example, you will have to update the connection
address, e.g. ip address. Otherwise, you can still run the examples by
providing the `--dummy` command line argument that will simulate
instrument output. The logging level can also be redirected to the
terminal using `--console` and the log-level changed by providing
`--info` or `--debug` options on the command line.

## Tests

We use `pytest` to provide some simple tests for some of the
functionallity of the package. However, to check if an instrument is
really working, one needs to have the instrument connected, which
makes testing harder. When the instruments are not available some
functionallity, such as the Qt layout, can still be tested using
"--dummy" mode. In this mode instrument parameters can return a
predefined value or the result of a function.

To run the tests use:

    python -m pytest


## Contribution guidelines

Feel free to contribute new drivers for hardware or other changes.

We use black to format the code, so please format your code
accordingly. The easiest way to achieve this is to install pre-commit
and use the config file we provide:

    pip install pre-commit
    # cd into repo
    pre-commit install

## How to cite this package

Please use the following [citation](https://doi.org/10.21105/joss.02688).

```
@article{Giesbrecht2022,
  doi = {10.21105/joss.02688},
  url = {https://doi.org/10.21105/joss.02688},
  year = {2022},
  publisher = {The Open Journal},
  volume = {7},
  number = {72},
  pages = {2688},
  author = {Grant Giesbrecht and Ariel Amsellem and Timo Bauer and Brian Mak and Brian Wynne and Zhihao Qin and Arun Persaud},
  title = {Hardware-Control: Instrument control and automation package},
  journal = {Journal of Open Source Software}
}
```

## Who do I talk to?

If you have questions, please contact Arun at apersaud@lbl.gov.

## Copyright and License

See the files COPYRIGHT and LICENSE in the top level directory

[![read-the-docs](https://readthedocs.org/projects/hardware-control/badge/?style=plastic)](https://readthedocs.org/projects/hardware-control/)
[![PyPI version](https://badge.fury.io/py/hardware-control.svg)](https://badge.fury.io/py/hardware-control)
[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white)](https://github.com/pre-commit/pre-commit)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

## What is this repository for? ###

The goal is to provide reusable code for hardware control using python and Qt.

Documentation can be found at [Read the Docs](https://readthedocs.org/projects/hardware-control/).

## How do I get set up? ###

The easiest way is to pip install the software:

    pip install hardware-control

## Tests

Currently, we do not provide unit tests, since for the backends tests can
really only be run with the hardware connected.  Instead of tests, we
provide example code that can be run after installing the package. All
examples can be run using a `--dummy` mode which will enable a
simulation mode that will make the software believe that all
instruments are connected to the program (some instrument will also
generate random data).

New controls and backends should therefore always implement a working
example.

## Contribution guidelines ###

Feel free to contribute new drivers for hardware or other changes.

We use black to format the code, so please format your code
accordingly. The easiest way to achieve this is to install pre-commit
and use the config file we provide:

    pip install pre-commit
    # cd into repo
    pre-commit install

## Who do I talk to? ###

If you have questions, please contact Arun at apersaud@lbl.gov.

## Copyright and License ###

See the files COPYRIGHT and LICENSE in the top level directory

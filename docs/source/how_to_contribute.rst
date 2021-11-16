How to contribute
=================

The source code can be found at::

  https://bitbucket.org/berkeleylab/hardware-control/

We use `pre-commit <https://pre-commit.com/>`_ to run checks and
format the code, so please install *pre-commit* using::

  pip install pre-commit

and then run::

  pre-commit install

from within the git repository of hardware control before creating
any commits that you want to share.

Using pre-commit ensures that the code will be formatted according to
the styl we expect, i.e., it will run black over the new code and some
other programs to ensure the code matches the coding style in the
repository.

Feedback, pull requests, and issues are welcome, including PRs for
new hardware.

We currently do all our work on the `main` branch and therefore pull
requests should be based off the latest available commit on this branch.

Furthermore, feel free to contact Arun at apersaud@lbl.gov directly to discuss possible
changes or ideas. If you plan to make a large contribution, we would especially like
to coordinate with you beforehand.

If you supply a new type of instrument driver, please also supply a
simple GUI that works with the driver and create an example for using it.
If you supply a new instrument driver of an already existing instrument type, for
example, a power supply, please ensure that it will work with Hardware Control's
existing GUIs.

Also, please add tests if feasible and make sure that the old tests
still run. Tests can be run using::

   python -m pytest

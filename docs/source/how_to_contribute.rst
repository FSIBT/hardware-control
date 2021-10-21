How to contribute
=================

The source code can be found at::

  https://bitbucket.org/berkeleylab/hardware-control/

We use `pre-commit <https://pre-commit.com/>`_ to run checks and
format the code, so please install *pre-commit* using::

  pip install pre-commit

and then run::

  pre-commit install

from within the git repository of hardware control, before creating
any commits that you want to share.

Using pre-commit ensures that the code will be formatted according to
the styl we expect, i.e., it will run black over the new code and some
other programs to ensure the code matches the coding style in the
repository.

Feedback and pull requests are welcome, including PRs for new hardware.

If you supply a new type of instrument driver, please also supply a simple GUI that works with the driver and create an example for it.
If you supply a new instrument driver of an already existing type, for example, a power supply, then please ensure that it will work with existing GUI.


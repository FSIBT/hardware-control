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

Feedback and pull requests are welcome, including PRs for new hardware.

We currently do not have any unit tests, since we find that UIs and
hardware are more difficult to test. Instead we rely on example
applications that we run regularly. If you supply new feature, please
provide an example (or unit tests, if applicable).

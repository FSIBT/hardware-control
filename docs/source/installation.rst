Installation
============

Hardware control requires python ≥ 3.6.

The code is available on `PyPi
<https://pypi.org/project/hardware-control>`_ and therefore can be
installed using pip using the following command::

  pip install hardware_control

Or use the *-U* flag to update the package::

  pip install -U hardware_control

Running pip install will also install all the required packages that
*hardware control* is relying on.

If you want to also work on the code, e.g. add new instruments or
supply bug fixes, you can clone the code from bitbucket using::

  git clone https://bitbucket.org/berkeleylab/hardware-control.git

and then cd into the repository and use::

  pip install -e .

This will install the package, but instead of copying the files it
creates links so that when you edit a file you don't need to rerun the
installation command (depending on your setup, you will need to
restart python though). If you however create a new file, you will
have to rerun the last command to create new links for the new files.

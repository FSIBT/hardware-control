import os
from setuptools import setup, Command
import setuptools


setup(
    name="hardware_control",
    packages=['hardware_control',
              'hardware_control.Adelphi',
              'hardware_control.CAEN',
              'hardware_control.Keysight',
              'hardware_control.Adam',
              'hardware_control.Sairem',
              'hardware_control.STM_motor',
              'hardware_control.Logfile'],
    package_data={'hardware-control': [os.path.join('hardware_control', 'icons', '*svg')]},
    install_requires=['pytest',
                      'tqdm',
                      'appdirs',
                      'matplotlib',
                      'numpy',
                      'pandas',
                      'pymodbus',
                      'pyqode.core',
                      'pyqode.python',
                      'pyvisa',
                      'pyvisa-py',
                      'scipy',
                      'setuptools',
                      'docopt',
                      'setuptools-scm'],
    setup_requires=['pytest-runner'],
    tests_require=['pytest'],
    scripts=[],
    author="Arun Persaud",
    author_email="apersaud@lbl.gov",
    description="",
    url="https://bitbucket.org/berkeleylab/hardware-control.git",
)

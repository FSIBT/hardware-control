import os
from setuptools import setup, Command
import setuptools


setup(
    name="hardware_control",
    packages=[
        "hardware_control",
        "hardware_control.DelayGenerator",
        "hardware_control.FlowController",
        "hardware_control.FunctionGenerator",
        "hardware_control.icons",
        "hardware_control.IOModule",
        "hardware_control.Oscilloscope",
        "hardware_control.PowerSupply",
        "hardware_control.widgets",
        "hardware_control.TemplateDeviceType",
    ],
    package_data={"hardware_control": [os.path.join("icons", "*svg")]},
    install_requires=[
        "appdirs",
        "colorama",
        "docopt",
        "matplotlib",
        "nidaqmx",
        "numpy",
        "pymodbus",
        "pyqt5",
        "pyqtgraph",
        "pytest",
        "pytest-runner",
        "pyvisa-py",
        "qtconsole",
        "setuptools",
        "setuptools-scm",
        "tqdm",
        "visa",
        "zmq",
    ],
    setup_requires=["pytest-runner"],
    tests_require=["pytest"],
    scripts=[],
    author="Arun Persaud",
    author_email="apersaud@lbl.gov",
    description="",
    url="https://bitbucket.org/berkeleylab/hardware-control.git",
)

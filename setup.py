import os
import setuptools

with open("README.md") as f:
    long_description = f.read()

with open("requirements.txt") as f:
    required = f.read().splitlines()

setuptools.setup(
    name="hardware-control",
    description="A package to write QT programs to control hardware",
    long_description=long_description,
    long_description_content_type="text/markdown",
    license="BSD-3-Clause-LBNL",
    packages=[
        "hardware_control",
        "hardware_control.base",
        "hardware_control.gui",
        "hardware_control.gui.controls",
        "hardware_control.gui.widgets",
        "hardware_control.instruments",
        "hardware_control.instruments.advantech",
        "hardware_control.instruments.alicat",
        "hardware_control.instruments.caen",
        "hardware_control.instruments.keysight",
        "hardware_control.instruments.ni",
        "hardware_control.instruments.picotech",
        "hardware_control.instruments.rigol",
        "hardware_control.instruments.siglent",
        "hardware_control.instruments.srs",
        "hardware_control.instruments.tdkl",
        "hardware_control.instruments.zmq",
        "hardware_control.icons",
    ],
    package_data={"hardware_control": [os.path.join("icons", "*svg")]},
    install_requires=required,
    setup_requires=["pytest-runner"],
    tests_require=["pytest"],
    scripts=[],
    author="Arun Persaud, Grant Giesbrecht, Timo Bauer",
    author_email="apersaud@lbl.gov",
    url="https://bitbucket.org/berkeleylab/hardware-control.git",
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
        "Development Status :: 5 - Production/Stable",
        "License :: OSI Approved :: BSD License",
        "Intended Audience :: Science/Research",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Topic :: Scientific/Engineering :: Physics",
    ],
    python_requires=">=3.6",
    include_package_data=True,
    zip_safe=False,
)

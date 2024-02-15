#!/usr/bin/env python3
from pathlib import Path

import setuptools
from setuptools import setup

this_dir = Path(__file__).parent

requirements = []
requirements_path = this_dir / "requirements.txt"
if requirements_path.is_file():
    with open(requirements_path, "r", encoding="utf-8") as requirements_file:
        requirements = requirements_file.read().splitlines()

module_name = "wyoming_porcupine3"
module_dir = this_dir / module_name
data_dir = module_dir / "data"
data_files = list(data_dir.rglob("*.pv")) + list(data_dir.rglob("*.ppn"))

version_path = module_dir / "VERSION"
data_files.append(version_path)
version = version_path.read_text(encoding="utf-8").strip()


# -----------------------------------------------------------------------------

setup(
    name=module_name,
    version=version,
    description="Wyoming Server for Porcupine 3",
    url="http://github.com/piitaya/wyoming-porcupine3",
    author="Paul Bottein",
    author_email="paul.bottein@nabucasa.com",
    license="MIT",
    packages=setuptools.find_packages(),
    package_data={module_name: [str(p.relative_to(module_dir)) for p in data_files]},
    install_requires=requirements,
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Topic :: Text Processing :: Linguistic",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    keywords="rhasspy wyoming porcupine wake word",
    entry_points={
        "console_scripts": ["wyoming-porcupine3 = wyoming_porcupine3.__main__:run"]
    },
)

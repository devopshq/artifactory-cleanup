#!/usr/bin/env python3
# -*- coding: utf-8 -*-


from setuptools import setup, find_packages  # noqa: H301

# read the contents of your README file
from pathlib import Path

this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text()

setup(
    name="artifactory-cleanup",
    version="0.3",
    description="Rules and cleanup policies for Artifactory",
    long_description=long_description,
    long_description_content_type="text/markdown",
    license="MIT",
    author="Alexey Burov",
    author_email="allburov@gmail.com",
    url="https://github.com/devopshq/artifactory-cleanup",
    keywords=["DevOpsHQ"],
    packages=find_packages(exclude=["tests"]),
    entry_points={
        "console_scripts": [
            "artifactory-cleanup=artifactory_cleanup.artifactorycleanup:ArtifactoryCleanup"
        ]
    },
    install_requires=[
        "hurry.filesize",
        "prettytable",
        "plumbum",
        "dohq-artifactory",
        "teamcity-messages",
    ],
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "License :: OSI Approved :: MIT License",
        "Natural Language :: English",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
    ],
    python_requires=">=3.6",
    include_package_data=True,
)

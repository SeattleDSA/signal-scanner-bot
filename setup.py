#!/usr/bin/env python

"""The setup script."""

from setuptools import setup, find_packages

with open("README.rst") as readme_file:
    readme = readme_file.read()

with open("HISTORY.rst") as history_file:
    history = history_file.read()

requirements = [
    "Click>=7.0",
    "tweepy>=3.9",
    "ujson>=3.1",
]

setup_requirements = [
    "pytest-runner",
]

test_requirements = [
    "pytest>=3",
]

setup(
    author="Madison Jane Bowden",
    author_email="bowdenm@spu.edu",
    python_requires=">=3.5",
    classifiers=[
        "Development Status :: 2 - Pre-Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Natural Language :: English",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
    ],
    description="A bot for conveying DSA scanner messages from Signal to Twitter",
    entry_points={
        "console_scripts": ["signal_scanner_bot=signal_scanner_bot.cli:main",],
    },
    install_requires=requirements,
    license="MIT license",
    long_description=readme + "\n\n" + history,
    include_package_data=True,
    keywords="signal_scanner_bot",
    name="signal_scanner_bot",
    packages=find_packages(include=["signal_scanner_bot", "signal_scanner_bot.*"]),
    setup_requires=setup_requirements,
    test_suite="tests",
    tests_require=test_requirements,
    url="https://github.com/AetherUnbound/signal_scanner_bot",
    version="0.1.0",
    zip_safe=False,
)

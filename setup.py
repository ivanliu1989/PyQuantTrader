#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset:4 -*-
"""
Created on Sat Jul 22 14:33:32 2017

@author: Ivan Liu
"""

import os.path
import codecs  # To use a consistent encoding
from setuptools import setup, find_packages

# Setup path
here = os.path.abspath(os.path.dirname(__file__))

# Get long description
with codecs.open(os.path.join(here, 'README.rst'), encoding='utf-8') as f:
    long_description = f.read()

# Package name
pname = 'PyQuantTrader'

setup(
    name=pname,
    version="0.1",
    packages=find_packages(),
    scripts=['say_hello.py'],

    # Project uses reStructuredText, so ensure that the docutils get
    # installed or upgraded on the target machine
    install_requires=['docutils>=0.3'],

    package_data={
        # If any package contains *.txt or *.rst files, include them:
        '': ['*.txt', '*.rst'],
        # And include any *.msg files found in the 'hello' package, too:
        'hello': ['*.msg'],
    },

    # metadata for upload to PyPI
    author="Tianxiang Liu",
    author_email="ivan.liuyanfeng@gmail.com",
    description="Backtesting & Live AB Testing Engine",
    long_description = long_description,
    license="PSF",
    keywords=['trading', 'development'],
    url="https://github.com/ivanliu1989/PyQuantTrader",   # project home page, if any

    extras_require={
        'plotting':  ['matplotlib'],
    },
)
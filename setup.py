#!/usr/bin/env python

from setuptools import setup, find_packages

from codecs import open
from os import path

here = path.abspath(path.dirname(__file__))

# Get the long description from the relevant file
with open(path.join(here, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='whatorganizer',
    version='0.1',
    description='What.CD organizer',
    long_description=long_description,
    author='Bob Malcolm',
    author_email='bob@gigatron.dk',
    url='https://github.com/ngitzarak/whatorganizer',
    #license=license,
    install_requires = [
        "python-libtorrent",
		"whatapi",
		"pymongo"
    ],
    packages=find_packages(exclude=('tests', 'docs')),
    package_data = {
        '': ['*.md']
    },
    zip_safe=True
)

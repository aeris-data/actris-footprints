#!/usr/bin/env python

from setuptools import setup

setup(
    name='common',
    version='0.1',
    description='common utils',
    author='Pawel Wolff',
    author_email='pawel.wolff@aero.obs-mip.fr',
    packages=[
        'common',
    ],
    install_requires=[
        'tqdm',
        'numpy',
        'pandas',
        'xarray',
        'dask',
    ],
    package_data={
        'common': [
            'resources/L4_vars_spec.json',
            'resources/L4_var_short_name_dict.json'
        ],
    }
)

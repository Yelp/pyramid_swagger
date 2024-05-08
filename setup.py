# -*- coding: utf-8 -*-
from __future__ import absolute_import

import io
import os

from setuptools import find_packages
from setuptools import setup


base_dir = os.path.dirname(__file__)
about = {}
with open(os.path.join(base_dir, "pyramid_swagger", "__about__.py")) as f:
    exec(f.read(), about)

with io.open(os.path.join(base_dir, "README.rst"), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name=about['__title__'],
    version=about['__version__'],

    description=about['__summary__'],
    long_description=long_description,
    license=about['__license__'],
    url=about["__uri__"],

    author=about['__author__'],
    author_email=about['__email__'],

    classifiers=[
        'Development Status :: 5 - Production/Stable',

        'Intended Audience :: Developers',
        'Topic :: Software Development :: Libraries :: Python Modules',

        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.10',

        'License :: OSI Approved :: BSD License',
    ],
    keywords='pyramid swagger validation',
    packages=find_packages(exclude=["contrib", "docs", "tests*"]),
    include_package_data=True,
    install_requires=[
        'bravado-core >= 4.8.4',
        'jsonschema >= 3.0.0',
        'pyramid',
        'simplejson',
    ],
)

import os

from setuptools import find_packages
from setuptools import setup


base_dir = os.path.dirname(__file__)
about = {}
with open(os.path.join(base_dir, "pyramid_swagger", "__about__.py")) as f:
    exec(f.read(), about)

with open(os.path.join(base_dir, "README.rst")) as f:
    long_description = f.read()

setup(
    name=about['__title__'],
    version=about['__version__'],

    description=about['__summary__'],
    long_description=long_description,
    license=about['__license__'],

    author=about['__author__'],
    author_email=about['__email__'],

    classifiers=[
        'Development Status :: 3 - Alpha',

        'Intended Audience :: Developers',
        'Topic :: Software Development :: Python Modules',

        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
    ],
    keywords='pyramid swagger validation',

    packages=find_packages(exclude=["contrib", "docs", "tests*"]),
    package_data={
        'pyramid_swagger': ['pyramid_swagger/swagger_spec_schemas/v1.2/*'],
    },
    include_package_data=True,
    install_requires=[
        'jsonschema',
        'pyramid',
        'simplejson',
    ],
)

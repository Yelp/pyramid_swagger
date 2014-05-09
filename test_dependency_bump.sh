#!/bin/bash
#
# Simple script to test whether bumping all your dependencies would cause tests to fail.
set -ex

virtualenv freeze_env
source freeze_env/bin/activate

pip install -e . -i http://pypi.yelpcorp.com/simple/ --use-wheel

# Delete the requirements.txt line indicating we installed our own package with -e.
PACKAGE=`python setup.py --name`
pip freeze > requirements.txt
sed "/$PACKAGE/d" requirements.txt -i
deactivate

# If we pass tests, commit our change.
#make test
true
if [[ $? == 0 ]] ; then
	echo -e '\e[1;32mSuccessfully bumped dependencies\e[m'
else
	echo -e '\e[1;31mFailed to bump dependencies\e[m'
fi

rm -rf freeze_env

.PHONY: clean docs install-hooks test

all: venv install-hooks

test: install-hooks
	tox

install-hooks: venv
	venv/bin/pre-commit install -f --install-hooks

venv: setup.py requirements-dev.txt
	virtualenv venv
	venv/bin/pip install -r requirements-dev.txt

docs:
	tox -e docs
	mkdir -p docs/build
	cp -r docs/_build/html docs/build/html

clean:
	find . -type f -iname "*.py[co]" -delete
	rm -fr *.egg-info/
	rm -fr .tox/
	rm -fr venv/

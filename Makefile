.PHONY: docs

test:
	tox

docs:
	tox -e docs
	mkdir -p docs/build
	cp -r docs/_build/html docs/build/html

clean:
	find . -type f -iname "*.py[co]" -delete
	rm -fr *.egg-info/
	rm -fr .tox/

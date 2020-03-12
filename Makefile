.DEFAULT: help
.PHONY: help deps lint test testreport build upload outdated clean

help:
	@echo "Please use \`$(MAKE) <target>' where <target> is one of the following:"
	@echo "  help       - show help information"
	@echo "  lint       - inspect project source code for errors"
	@echo "  test       - run project tests"
	@echo "  testreport - run project tests and open HTML coverage report"
	@echo "  build      - build project packages"
	@echo "  upload     - upload built packages to package repository"
	@echo "  outdated   - list outdated project requirements"
	@echo "  clean      - clean up project environment and all the build artifacts"

deps:
	python -m pip install pip==20.0.2 setuptools==46.0.0 wheel==0.34.2
	python -m pip install -e .[dev,test]

lint:
	python -m flake8 cstarmigrate tests

test:
	python -m pytest

testreport:
	python -m pytest --cov-report=html
	xdg-open htmlcov/index.html

build:
	python setup.py sdist bdist_wheel

upload: build
	python -m twine upload dist/*

outdated: bootstrap
	python -m pip list --outdated --format=columns

clean:
	rm -rf *.egg .eggs *.egg-info build dist htmlcov log py*

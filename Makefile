.DEFAULT: help
.PHONY: help bootstrap build lint test testreport outdated upload clean

VENV = .venv
PYTHON_BIN ?= python3
PYTHON = $(VENV)/bin/$(PYTHON_BIN)

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

bootstrap: $(VENV)/bin/activate
$(VENV)/bin/activate:
	$(PYTHON_BIN) -m venv $(VENV)
	$(PYTHON) -m pip install -U pip==21.3.1 setuptools==59.6.0 wheel==0.37.0
	$(PYTHON) -m pip install -e .[dev,test]

build: bootstrap
	$(PYTHON) setup.py sdist bdist_wheel

lint: bootstrap
	$(PYTHON) -m flake8 cstarmigrate tests

test: bootstrap
	$(PYTHON) -m pytest

testreport: bootstrap
	$(PYTHON) -m pytest --cov-report=html
	xdg-open htmlcov/index.html

outdated: bootstrap
	$(PYTHON) -m pip list --outdated --format=columns

upload: build
	$(PYTHON) -m twine upload dist/*

clean:
	rm -rf *.egg-info .eggs build dist htmlcov $(VENV)

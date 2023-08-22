.DEFAULT: help
.PHONY: help bootstrap build lint test testreport outdated clean

VENV=.venv
PYTHON_BIN?=python3
PYTHON=$(VENV)/bin/$(PYTHON_BIN)

help:
	@echo "Please use \`$(MAKE) <target>' where <target> is one of the following:"
	@echo "  help       - show help information"
	@echo "  lint       - inspect project source code for errors"
	@echo "  test       - run project tests"
	@echo "  testreport - run project tests and open HTML coverage report"
	@echo "  build      - build project packages"
	@echo "  outdated   - list outdated project requirements"
	@echo "  clean      - clean up project environment and all the build artifacts"

bootstrap: $(VENV)/bin/activate
$(VENV)/bin/activate:
	$(PYTHON_BIN) -m venv $(VENV)
	$(PYTHON) -m pip install -U build==0.10.0 pip==23.2.1 setuptools==68.1.2 wheel==0.41.2
	$(PYTHON) -m pip install -e .[dev,test]

build: bootstrap
	$(PYTHON) -m build -s -w

lint: bootstrap
	$(PYTHON) -m flake8 cstarmigrate tests

test: bootstrap
	$(PYTHON) -m pytest

testreport: bootstrap
	$(PYTHON) -m pytest --cov-report=html
	xdg-open htmlcov/index.html

outdated: bootstrap
	$(PYTHON) -m pip list --outdated --format=columns

clean:
	rm -rf *.egg-info .eggs build dist htmlcov $(VENV)

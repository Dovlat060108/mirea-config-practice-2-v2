PYTHON ?= python3

.PHONY: run test build demo-errors
run:
	$(PYTHON) -B src/main.py examples/junit.xml

test:
	PYTHONPATH=src $(PYTHON) -B -m unittest discover -s tests -v

build:
	PYTHONPATH=src $(PYTHON) -B -c "import config, main; print('Syntax OK')"

demo-errors:
	PYTHONPATH=src $(PYTHON) -B examples/demo_errors.py

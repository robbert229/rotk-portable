PYTHON ?= python3

.PHONY: help test
help:
	@echo "make test  Run the regression suite"

test:
	$(PYTHON) -m unittest discover -s tests -v

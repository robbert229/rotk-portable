PYTHON ?= python3

.PHONY: help test lint
help:
	@echo "make test  Run symbol lint and the regression suite"

	@echo "make lint  Validate the symbol database"

test: lint
	$(PYTHON) -m unittest discover -s tests -v

SYMBOL_FILES ?= $(wildcard re/symbols/*.csv)
lint:
	$(PYTHON) tools/symdb.py lint $(SYMBOL_FILES)

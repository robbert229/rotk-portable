PYTHON ?= python3

.PHONY: help test lint
help:
	@echo "make test  Run symbol lint and the regression suite"

	@echo "make lint  Validate the symbol database"
	@echo "make ghidra  Analyze EXE and apply the symbol database"
	@echo "make ghidra-export  Write new auto rows to GHIDRA_EXPORT"
	@echo "make srcpaths  Regenerate the packed ROTK.exe path inventory and module map"

test: lint
	$(PYTHON) -m unittest discover -s tests -v

SYMBOL_FILES ?= $(wildcard re/symbols/*.csv)
lint:
	$(PYTHON) tools/symdb.py lint $(SYMBOL_FILES)

ROTK_GAME_DIR ?= $(HOME)/Games/lord-of-the-rings-the-return-of-the-king/drive_c/Program Files (x86)/EA GAMES/LOTR The Return of the King tm
EXE ?= $(if $(ROTK_UNPACKED_EXE),$(ROTK_UNPACKED_EXE),$(ROTK_GAME_DIR)/ROTK.exe)
GHIDRA_EXPORT ?= out/ghidra/unassigned.csv

.PHONY: ghidra ghidra-export
ghidra:
	$(PYTHON) -BI tools/ghidra_build.py "$(EXE)"

ghidra-export:
	$(PYTHON) -BI tools/ghidra_build.py "$(EXE)" --export-auto "$(GHIDRA_EXPORT)"

.PHONY: srcpaths
srcpaths:
	$(PYTHON) -I tools/srcpaths.py "$(ROTK_GAME_DIR)/ROTK.exe" > re/strings/source_paths.txt
	$(PYTHON) -I tools/srcpaths.py "$(ROTK_GAME_DIR)/ROTK.exe" --modules > docs/modules/README.md

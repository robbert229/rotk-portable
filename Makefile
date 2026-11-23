PYTHON ?= python3

.PHONY: help test lint
help:
	@echo "make test  Run symbol lint and the regression suite"

	@echo "make lint  Validate the symbol database"
	@echo "make ghidra  Analyze EXE and apply the symbol database"
	@echo "make ghidra-export  Write new auto rows to GHIDRA_EXPORT"
	@echo "make srcpaths  Regenerate the packed ROTK.exe path inventory and module map"
	@echo "make richhdr  Report Rich headers for installed game PEs"
	@echo "make toolchain  Fetch MSVC 7.0 and initialize dedicated Wine"
	@echo "make hello  Build and verify the MSVC smoke test"
	@echo "make doctor  Report MSVC and Wine diagnostics"

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
	@# Write to temp files and rename on success so a failed run keeps the tracked outputs.
	set -e; trap 'rm -f re/strings/source_paths.txt.tmp docs/modules/README.md.tmp' EXIT; \
	$(PYTHON) -I tools/srcpaths.py "$(ROTK_GAME_DIR)/ROTK.exe" > re/strings/source_paths.txt.tmp; \
	$(PYTHON) -I tools/srcpaths.py "$(ROTK_GAME_DIR)/ROTK.exe" --modules > docs/modules/README.md.tmp; \
	mv re/strings/source_paths.txt.tmp re/strings/source_paths.txt; \
	mv docs/modules/README.md.tmp docs/modules/README.md

.PHONY: richhdr
richhdr:
	find "$(ROTK_GAME_DIR)" -type f \( -iname '*.exe' -o -iname '*.dll' -o -iname '*.sys' \) -print0 | \
		sort -z | xargs -0 -r $(PYTHON) -I tools/richhdr.py

.PHONY: toolchain hello doctor
toolchain:
	$(PYTHON) -I tools/msvc.py fetch

hello:
	mkdir -p out/hello
	$(PYTHON) -I tools/msvc.py cl /nologo /c /showIncludes /Foout/hello/hello.obj tools/hello/hello.c
	$(PYTHON) -I tools/msvc.py link /nologo /out:out/hello/hello.exe out/hello/hello.obj
	$(PYTHON) -I tools/hello/check.py out/hello/hello.obj out/hello/hello.exe

doctor:
	$(PYTHON) -I tools/msvc.py doctor

ROTK_UNPACKED_EXE ?= out/unpacked/ROTK_unpacked.exe

.PHONY: validate-dump
validate-dump:
	@$(PYTHON) -I tools/validate_dump.py "$(ROTK_UNPACKED_EXE)"

.PHONY: corpus-formats
corpus-formats:
	$(PYTHON) -I tools/corpus_formats.py --game-dir "$(ROTK_GAME_DIR)"

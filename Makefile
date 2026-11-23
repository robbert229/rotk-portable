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
	@echo "make corpus  Regenerate the committed retail corpus CSVs"
	@echo "make corpus-check  Compare freshly generated corpus CSVs with HEAD"
	@echo "make scw-chunks  Generate the detailed SCW inventory under out/corpus"

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

CORPUS_DIR := re/corpus
CORPUS_OUTPUT ?= $(CORPUS_DIR)
CORPUS_STEPS := corpus-manifest corpus-formats pecat assetindex filerefs libscan scw-summary corpus-samples
CORPUS_CSVS := manifest.csv formats.csv binaries.csv pe_sections.csv pe_imports.csv \
	assets.csv assets_avi.csv assets_scw.csv filerefs.csv listed_files.csv libraries.csv \
	scw_chunk_summary.csv samples.csv
CORPUS_PYTHON = $(PYTHON) -BI
export ROTK_GAME_DIR

.PHONY: corpus corpus-check $(CORPUS_STEPS)
corpus corpus-check:
	@set -eu; scratch=$$(mktemp -d); trap 'rm -rf "$$scratch"' EXIT; \
	for step in $(CORPUS_STEPS); do \
		$(MAKE) --no-print-directory "$$step" CORPUS_OUTPUT="$$scratch"; \
	done; \
	if [ "$@" = corpus ]; then \
		for csv in $(CORPUS_CSVS); do \
			mv "$$scratch/$$csv" "$(CORPUS_DIR)/$$csv"; \
		done; \
	else \
		status=0; \
		for csv in $(CORPUS_CSVS); do \
			git show "HEAD:$(CORPUS_DIR)/$$csv" > "$$scratch/committed"; \
			diff -u --label "HEAD:$(CORPUS_DIR)/$$csv" --label "generated/$$csv" \
				"$$scratch/committed" "$$scratch/$$csv" || status=1; \
		done; \
		[ "$$status" -eq 0 ]; \
		echo "Corpus CSVs match HEAD."; \
	fi

corpus-manifest:
	$(CORPUS_PYTHON) tools/corpus.py --install-only --output "$(CORPUS_OUTPUT)/manifest.csv"

corpus-formats:
	$(CORPUS_PYTHON) tools/corpus_formats.py --manifest "$(CORPUS_OUTPUT)/manifest.csv" \
		--output "$(CORPUS_OUTPUT)/formats.csv"

pecat:
	$(CORPUS_PYTHON) tools/pecat.py --output-dir "$(CORPUS_OUTPUT)"

assetindex:
	$(CORPUS_PYTHON) tools/assetindex.py --manifest "$(CORPUS_OUTPUT)/manifest.csv" \
		--out-dir "$(CORPUS_OUTPUT)"

filerefs:
	$(CORPUS_PYTHON) tools/filerefs.py --output-dir "$(CORPUS_OUTPUT)"

libscan:
	$(CORPUS_PYTHON) tools/libscan.py --output "$(CORPUS_OUTPUT)/libraries.csv"

scw-summary:
	@set -eu; tmp=$$(mktemp); trap 'rm -f "$$tmp"' EXIT; \
	$(CORPUS_PYTHON) tools/scwdump.py --summary-csv > "$$tmp"; \
	mv "$$tmp" "$(CORPUS_OUTPUT)/scw_chunk_summary.csv"

corpus-samples:
	@set -eu; tmp=$$(mktemp); trap 'rm -f "$$tmp"' EXIT; \
	$(CORPUS_PYTHON) tools/samples.py refresh --corpus-manifest "$(CORPUS_OUTPUT)/manifest.csv" > "$$tmp"; \
	mv "$$tmp" "$(CORPUS_OUTPUT)/samples.csv"

.PHONY: scw-chunks corpus-verify refs samples
scw-chunks:
	@set -eu; tmp=$$(mktemp); trap 'rm -f "$$tmp"' EXIT; \
	$(CORPUS_PYTHON) tools/scwdump.py --chunks-csv > "$$tmp"; \
	mkdir -p out/corpus; \
	mv "$$tmp" out/corpus/scw_chunks.csv

corpus-verify:
	@ROTK_ISO_DIR="$(ROTK_ISO_DIR)" $(CORPUS_PYTHON) tools/corpus.py --verify

refs:
	$(CORPUS_PYTHON) tools/refs.py fetch

samples:
	$(CORPUS_PYTHON) tools/samples.py fetch

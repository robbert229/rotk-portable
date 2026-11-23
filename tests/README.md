# Tool regression tests

Run `make test` from the repository root. Sample tests look for `LoadOnce.scw`,
`Ring.GEO`, and `Ring.txw` in `assets/samples/`. Set `ROTK_SAMPLES_DIR` to use
samples from another checkout. Tests skip individually when their input is
missing. See [the format registry](../docs/formats/index.md) for sample extraction.
Retail PACs are outside the test suite. The `unpac` test extracts a synthetic
member split across two packs, so it runs without retail data.

The harness checks the exact bytes of SCW stdout, the OBJ, every PNG, and the
synthetic extracted member. It runs each CLI in Python isolated mode and uses
temporary output directories. SCW receives a relative filename so changing the
samples directory does not change its output. PNG hashes include the zlib
compressed bytes, which can differ between compression implementations.

After reviewing an intentional output change, regenerate and review the hashes
from the repository root with all three inputs available.

```sh
ROTK_SAMPLES_DIR=/path/to/samples python3 tests/test_tools.py --update
git diff -- tests/expected.json
```

Commit only the reviewed hashes. Keep samples and generated outputs local.

The corpus consistency tests cross-check the committed install identities and
coverage without retail files. With the retail install available, the SCW
regression compares the per-file summary byte for byte and cross-checks it
against the detailed walk. Run `make corpus-check` to verify all generated
corpus CSVs against Git `HEAD`, or `make scw-chunks` to keep a local copy
of the detailed walk in `out/corpus/`.

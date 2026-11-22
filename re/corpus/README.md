# Corpus manifest

Run `python3 -I tools/corpus.py` to regenerate `re/corpus/manifest.csv` from
the default game installation. Set `ROTK_GAME_DIR` to use another installation.

For retail media, extract or mount the discs first. Set `ROTK_ISO_DIR` to
the directory containing the three PACs or their disc subdirectories, or
pass the PAC paths in disc order with `--pac data_1.pac data_2.pac data_3.pac`.

Install paths are relative to the game directory. PAC paths are relative to
the archive TOC and correspond to paths under the installed `Data/` directory
[observed: docs/formats/pac.md]. A member spanning packs is attributed to the
pack containing its first byte. The CSV is sorted by origin and path.

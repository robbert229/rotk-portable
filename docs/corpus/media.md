# Retail PC media and PAC verification

## Compare an installation with the retail discs

Mount the three retail discs read-only or extract their files into separate
directories. Set `ROTK_ISO_DIR` to their common parent. The verifier looks
recursively for one each of `data_1.pac`, `data_2.pac` and `data_3.pac`.
Set `ROTK_GAME_DIR` for an installation outside the playbook's default.
[observed: `tools/corpus.py` and synthetic three-pack test]

```sh
make corpus-verify ROTK_ISO_DIR=/path/to/disc-trees
```

For discs mounted under different parents, pass the PAC paths in disc order.

```sh
python3 -I tools/corpus.py --verify --pac \
  /mnt/install1/data_1.pac /mnt/install2/data_2.pac /mnt/play/data_3.pac
```

The report lists the status, path, byte size and SHA-256 for the two sides,
then totals each status. It compares paths case-insensitively after prefixing
PAC member paths with `Data/`. Matching sizes and hashes produce `match`.
Differing sizes or hashes produce `mismatch` and exit status 1. `pac-only`
and `install-only` indicate a path present on one side and are reported
without changing the exit status. The install side covers all files under
`Data/`. Check both one-sided counts when verifying coverage.
[observed: `tools/corpus.py` and `test_verify_reports_four_statuses`]

The English retail TOC contains 99 records. The 16 records with size zero
describe directories such as `Game`, its level folders, `Movies`, `Player`
and `Special`. They consume TOC space and no payload bytes, leaving 83 file
members. The three PACs provide successive windows on one logical stream, so
the verifier hashes the whole member even when it spans two packs.
[observed: [PAC TOC and member inventory](../formats/pac.md)]

The [PAC spec](../formats/pac.md) records a previous run in which all 83 SHA-256
values matched the installed files. The checked-in install manifest has 83
files under `Data/`. A retail run of this verifier remains pending the owner's
ISOs. The earlier comparison used the documented English set, whose exact
Redump track identity is unknown.
[observed: PAC spec and [install manifest](../../re/corpus/manifest.csv);
unknown: raw track identity and result of the pending run]

## Inventory images and disc trees

```sh
mkdir -p out
python3 -I tools/corpus.py \
  --disc-tree /mnt/install1 /mnt/install2 /mnt/play \
  --disc-image /path/to/disc1.iso /path/to/disc2.iso /path/to/disc3.iso \
  > out/disc-manifest.csv
```

Each list starts with disc 1. Matching list positions share an origin
(`disc1`, `disc2`, and so on). Either list can be supplied by itself.
Image rows contain the image basename and hash all bytes of the supplied
file. File rows contain paths relative to the disc root and hash each file
in that mounted or extracted tree. The CSV records byte sizes and SHA-256
values. The tool reads the ISO 9660 primary volume label from 2048-byte
sector images or single-track raw Mode 1 images with 2352-byte sectors.
For tree-only input or an image with an unreadable label, supply one known
label per disc with `--disc-label`. An empty argument requests automatic
detection, leaving the CSV field blank if the label is unavailable.
These options emit the disc CSV on stdout. Adding `--verify` also runs the
PAC comparison and sends its report to stderr.
[observed: `tools/corpus.py` and `test_disc_inventory`]

## Public media reference

[media.csv](../../re/corpus/media.csv) records published PC CD track sizes
in bytes and CRC-32, MD5 and SHA-1 for track 1 of each listed disc. Each row
links directly to the preservation record. These hashes cover the raw
2352-byte-per-sector Mode 1 track (`.bin`). Compare them with a dump in
that layout. A cooked ISO contains 2048-byte user-data sectors and has a
different byte layout. Blank fields mark facts unavailable in the cited
record. [observed: linked Redump Tracks and Files tables]

| Region and edition | Discs | Published volume labels, in order | Evidence |
|---|---:|---|---|
| USA, Original / The EA Games Collection | 3 | Unknown | [observed: [1](https://redump.info/disc/40822), [2](https://redump.info/disc/40821), [3](https://redump.info/disc/40820)] |
| USA, Original (Alt) | 3 | `ROTK Install 1`, `ROTK Install 2`, `ROTK Play Disc` | [observed: [1](https://redump.info/disc/64897), [2](https://redump.info/disc/64898), [3](https://redump.info/disc/64899)] |
| Europe, Original | 3 | `ROTK Install 1`, `ROTK Install 2`, `ROTK Play Disc` | [observed: [1](https://redump.info/disc/92581), [2](https://redump.info/disc/92582), [3](https://redump.info/disc/92583)] |
| Europe, EA Games Classics | 3 | `ROTK_INSTALL_1`, `ROTK_INSTALL_2`, `ROTK Play Disc` | [observed: [1](https://redump.info/disc/133153), [2](https://redump.info/disc/133154), [3](https://redump.info/disc/133155)] |
| Finland, EA Classics | 3 | `ROTK Install 1`, `ROTK Install 2`, `ROTK Play Disc` | [observed: [1](https://redump.info/disc/109739), [2](https://redump.info/disc/109740), [3](https://redump.info/disc/109741)] |
| Sweden, Original | 3 | `ROTK Install 1`, `ROTK Install 2`, `ROTK Play Disc` | [observed: [1](https://redump.info/disc/113220), [2](https://redump.info/disc/113221), [3](https://redump.info/disc/113222)] |
| Japan, Original / EA Best Selections | 3 | `ROTK_JP_1`, `ROTK_JP_2`, `ROTK_JP_3` | [observed: [1](https://redump.info/disc/35674), [2](https://redump.info/disc/35673), [3](https://redump.info/disc/35675)] |
| Korea, Original | 3 | `ROTK_KR_1`, `ROTK_KR_2`, `ROTK_KR_3` | [observed: [1](https://redump.info/disc/139408), [2](https://redump.info/disc/139409), [3](https://redump.info/disc/139410)] |
| China, Original | 3 | Unknown | [observed: [1](https://redump.info/disc/76184), [2](https://redump.info/disc/76185), [3](https://redump.info/disc/76186)] |

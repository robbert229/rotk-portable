# Retail corpus index

Run `make corpus` from the repository root to regenerate the install-derived
CSVs. It reads the retail install selected by `ROTK_GAME_DIR`, with the
[playbook default](../../docs/agent-playbook.md#2-environment) as a fallback.
It stages the full run before publishing the CSVs. Run `make corpus-check`
to regenerate in a temporary directory and diff against the files in Git
`HEAD`. See the [corpus overview](../../docs/corpus/README.md) for findings.

## Committed tables

Row counts exclude headers [observed: checked-in CSVs]. A dash in the make
column denotes a curated table. The install-derived tables are regenerated in
the order shown. Paths are case-preserving and install-relative unless the
schema gives another origin. Sizes are bytes and `sha256` identifies the
source file's exact bytes. Blank cells denote unavailable or inapplicable
fields, except where a table defines an explicit status. `evidence` records
provenance and the observation or inference.

| CSV | Rows | Contents | Generator or source | Make target |
|---|---:|---|---|---|
| [manifest.csv](manifest.csv) | 120 | Installation file identities | [corpus.py](../../tools/corpus.py) | `corpus-manifest` |
| [formats.csv](formats.csv) | 120 | Format classification and parser probes | [corpus_formats.py](../../tools/corpus_formats.py) | `corpus-formats` |
| [binaries.csv](binaries.csv) | 15 | PE headers, directories and metadata | [pecat.py](../../tools/pecat.py) | `pecat` |
| [pe_sections.csv](pe_sections.csv) | 66 | PE section headers and raw entropy | `pecat.py` | `pecat` |
| [pe_imports.csv](pe_imports.csv) | 2,019 | Normal and delay-loaded import thunks | `pecat.py` | `pecat` |
| [assets.csv](assets.csv) | 105 | Non-PE metadata | [assetindex.py](../../tools/assetindex.py) | `assetindex` |
| [assets_avi.csv](assets_avi.csv) | 37 | AVI stream and index metadata | `assetindex.py` | `assetindex` |
| [assets_scw.csv](assets_scw.csv) | 44 | SCW headers, COTS TOCs and standalone LRTC details | `assetindex.py` | `assetindex` |
| [filerefs.csv](filerefs.csv) | 142 | PE path strings and resolution | [filerefs.py](../../tools/filerefs.py) | `filerefs` |
| [listed_files.csv](listed_files.csv) | 108 | Installer and install listing entries | `filerefs.py` | `filerefs` |
| [libraries.csv](libraries.csv) | 200 | Binary library and toolchain fingerprints | [libscan.py](../../tools/libscan.py) | `libscan` |
| [scw_chunk_summary.csv](scw_chunk_summary.csv) | 44 | SCW counts and walk coverage | [scwdump.py](../../tools/scwdump.py) | `scw-summary` |
| [samples.csv](samples.csv) | 52 | Curated sample choices with manifest identities | [samples.py](../../tools/samples.py) refreshes sizes and hashes | `corpus-samples` |
| [media.csv](media.csv) | 27 | Published retail PC disc-track identities | Curated from cited disc records | — |
| [reference_sources.csv](reference_sources.csv) | 28 | Pinned upstream, toolchain and retail comparison sources | Curated input to [refs.py](../../tools/refs.py) | — |
| [editions.csv](editions.csv) | 67 | Pressings, demos, reissues and engine leads | Curated from the install and cited sources | — |

## CSV schemas

[observed: CSV headers and generator output.]

### Install manifest and format coverage

- **manifest.csv**. `origin` is `install` in the committed baseline. The optional PAC mode uses `pac:data_N` for the pack containing the member's first byte. `path` is relative to the install root or archive TOC, respectively. `size` and `sha256` cover the whole file or member.
- **formats.csv**. `path`, `sha256`, `size` identify an installed file. `ext` is the original suffix, `detected_format` is the content classification, and `magic_hex` is up to eight initial bytes in hex. `spec` and `tool` are repo-relative links. `parse_status` is `ok`, `fail` or `n/a`. `parse_note` gives the probe result or reason.

### PE catalogue

- **binaries.csv**. `path`, `sha256`, `size` identify an image. `machine` is the COFF machine, `timestamp_utc` its header timestamp, and `linker_version`, `os_version`, `subsystem_version` and `subsystem` are optional-header values. `image_base` is the preferred load address. `entry_rva` and `entry_section` locate the entry point. `checksum_stored` and `checksum_computed` are the PE checksums. `characteristics` and `dll_characteristics` are header flags. `section_count` counts section headers.
- The `debug_directory` lists type, file offset and size. `codeview_format`, `pdb_path`, `pdb_guid`, `pdb_timestamp` and `pdb_age` describe CodeView records, in corresponding list order. `CompanyName`, `FileDescription`, `FileVersion`, `ProductName`, `ProductVersion`, `OriginalFilename` and `InternalName` are version-resource strings. `rich_status`, `rich_key`, `rich_checksum`, `rich_record_only_checksum` and `rich_records` describe validation, XOR key, computed checksums and decoded Rich records.
- `import_dlls` and `import_function_counts` give normal imports by DLL. `delay_import_rva` and `delay_import_size` locate the delay directory. `delay_import_dlls` and `delay_import_function_counts` give delay imports by DLL. `export_dll_name` and `export_count` give the export name and address-table slot count. `tls_present` reports a TLS directory. `resource_types` counts resource language leaves by type. `overlay_size` counts bytes after headers and file-backed sections. `evidence` cites the PE structures used. See [list encoding and debug conventions](../../docs/corpus/binaries.md).
- **pe_sections.csv**. `path` joins to the image. `index` is the zero-based section-table slot and `name` the escaped section name. `va` is the section RVA, `vsize` its virtual size, and `raw_off` and `raw_size` locate its on-disk range. `characteristics` stores section flags, `entropy` measures bits per byte across the raw range, and `evidence` locates the header.
- **pe_imports.csv**. `path` joins to the image. `dll` and `function_or_ordinal` identify the import, with numeric ordinals prefixed by `#`. `kind` identifies the ordinary or delay-load directory and `evidence` locates the thunk.

### Asset index and scene walk

- **assets.csv**. `path`, `sha256`, `size` identify the file. `format` identifies its family and `container` its structural subtype when available. `width` and `height` are pixels. `zone_count` and `bank_count` count named COTS TOC groups. `frame_count`, `fps` and `duration_seconds` describe video. `mesh_count`, `texture_count`, `element_count`, `line_count` and `section_count` count meshes, textures, XML elements, text lines and text sections respectively. `encoding` describes text decoding. `details` carries format-specific fields as semicolon-separated key/value pairs with percent-encoded values. `evidence` cites the structures inspected.
- **assets_avi.csv**. `path`, `sha256`, `format`, `size` join to the asset. `riff_size` is the RIFF size field, `bytes_after_riff` counts trailing bytes. `stream_count` counts parsed streams and `declared_stream_count` comes from the main header. `fourcc` and `codec` identify video encoding. `width`, `height`, `frame_count` and `main_header_frame_count` capture stream dimensions and the two frame counts. `rate` and `scale` determine `fps` and `duration_seconds`. `has_audio`, `has_index` and `index_types` describe audio and indexing. `evidence` cites AVI structures.
- **assets_scw.csv**. `path`, `sha256`, `format`, `size` join to the asset. `container` is COTS or LRTC. `u32_04_unknown` and `reserved_words` preserve raw header fields. `header_size` gives the LRTC header length. `toc_bytes`, `toc_version`, `toc_count` describe the COTS TOC. `chunk_count` counts inner TOC and leading LLIF for COTS or stream chunks for LRTC. `zone_count`, `missing_zone_count`, `bank_count`, `other_igc_count` and `other_record_count` count TOC categories after initial load. `toc_gap` measures the gap between the record table and name pool. `llif_offset` and `llif_size` locate the leading filler. `chain_contiguous`, `chain_end` and `bytes_after_chain` describe the COTS TOC region chain. `record_names`, `record_kinds`, `record_offsets`, `record_sizes`, `embedded_doc_names` and `nested_lrtc_offsets` are parallel lists in TOC order. `chunks` names the COTS entries or lists LRTC tags, offsets and sizes. `cohs_index` lists tagged words in standalone LRTC RDHS-prefixed COHS payloads. `walk_end` is the standalone LRTC walk endpoint. `evidence` cites the structures inspected.
- **scw_chunk_summary.csv**. `path` joins to the scene and `container` gives its root tag. `COTS`, `LRTC`, `RVWS`, `COHS`, `ONOS`, `DDAP`, `LLIF` count rows per tag including structural headers. `max_depth` counts parent links from the root, which is depth zero. `walked_to_eof` is `yes` or `no` and `leftover_bytes` is the file size minus the walked end. See the [per-tag totals and detailed schema](../../docs/formats/scw.md#chunk-inventory).

### References, fingerprints and samples

- **filerefs.csv**. `source` names the PE, `offset` is its hex file offset, and `section` is the containing PE section. `encoding` describes the string bytes, `string` is the raw spelling, and `normalised` is the comparison key. `kind` identifies literals, directories or patterns. `resolves_to` gives matching paths and `status` records the resolution outcome.
- **listed_files.csv**. `source` is the listing, `line` the physical line number, and `path` the listed spelling. `type` is the installer type code or file, directory or pattern. `size_if_given` is the listed byte count. `present_in_install` indicates whether the path or pattern matched.
- **libraries.csv**. `binary` is the inspected file and `library` and `version` describe the candidate attribution. `evidence_kind` identifies the fingerprint type, `offset` locates it in the file, `evidence` describes the anchor, and `confidence` tags the attribution.
- **samples.csv**. `sample_id` is the stable sample name. `source_origin` identifies install or PAC input, with `source_path` relative to that root. `sha256` and `size` pin the bytes. `format`, `variant` and `why_selected` document coverage. `used_by_tests` flags samples also copied to the flat test directory.

### Curated catalogues

- **media.csv**. `region`, `languages`, `editions` and `version` identify the published release. `disc` and `disc_count` give disc order and set size. `disc_title`, `volume_label` and `disc_serial` record identifiers. `track`, `track_type` and `track_size` describe the raw track. `crc32`, `md5` and `sha1` are raw-track digests. `source_url` and `evidence` identify the record and provenance.
- **reference_sources.csv**. `kind` identifies an archive, toolchain file or retail binary. `upstream_name` and `version` describe the reference. `path` is relative to its cache, checkout or install, according to `kind`. `upstream_url` is the project or provenance link, `download_url` is the archive location, and `sha256` pins the bytes. `license` records the stated terms, `binaries` lists relevant installed binaries, `evidence` records the relationship and `reference_revision` pins the upstream revision where available.
- **editions.csv**. `platform`, `region`, `edition/label`, `version`, `release_date` and `product_code/serial` identify the edition. `executable_or_main_binary` names the program. `known_hashes_or_db_ids` distinguishes hashes and catalogue IDs. `debug_symbols_or_map_files_known` records known sidecars or embedded debug clues. `notes` describes the edition and open questions. `source_url` links supporting sources and `evidence` tags the claim.

## Local outputs and pending work

- `make samples` materialises the verified sample paths and flat regression copies in gitignored `assets/samples/`.
- `make refs` fetches or verifies reference archives in gitignored `out/refs/` and can verify pinned files in a local MSVC checkout.
- `make scw-chunks` generates the 92,419-row detailed inventory under gitignored `out/corpus/`. Local disc inventories and later comparison CSVs can also go under `out/`.
- The retail ISO/PAC comparison needs local media under `ROTK_ISO_DIR`. Run `make corpus-verify` with the three packs available. See [retail media](../../docs/corpus/media.md).
- After M1, rerun `filerefs.py`, `libscan.py` and `pecat.py` on the validated unpacked executable, retaining the packed baseline and keeping comparisons under `out/`.

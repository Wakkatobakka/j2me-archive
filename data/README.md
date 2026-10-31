# Reading the metadata

This is a bibliographic snapshot prepared October 30, 2026. It contains no game binaries, source descriptions, screenshots, or cover art.

`catalog.json` contains the main catalog entries, the ten recorded Omni inputs, source-record keys, and review notes. `catalog.csv` is a smaller title-level export. `search.json` is generated search text for those entries. It is not an independent source.

`library-index.json` indexes the separate bibliographic source records. `file-index.json` indexes the separate JAR/JAD and archive-file inventory references. Each index item points to a metadata shard in `sources/`. The record inspector reads those shards on demand, rather than loading all edition data into a phone at once.

## Field meanings

| Field | Meaning |
| --- | --- |
| `id`, `key` | Stable identifier within this snapshot; a source prefix prevents collisions. |
| `slug` | Path to the main catalog page. |
| `listed_year` | Year listed by the explicit J2ME directory. It is not independently verified against an original release. |
| `genres` | Genre labels from the explicitly J2ME fact table, or the attributed candidate source for an Omni-only entry. |
| `omni` | Recorded input edition from the public Omni Player guide. `null` means it is not one of the ten starting recovery records. |
| `source_records` | Source keys and their connection type. A normalized title or reviewed alias remains a candidate, not a verified build identity. |
| `source_variant_groups` | Sum of attached source edition-label groups. Repeated labels can describe the same build. This is not a count of verified distinct editions. |
| `languages_as_labeled`, `resolutions_as_labeled` | Labels observed in attached sources. They were not checked inside binaries. |
| `page_fact_tables` | The original bibliographic tables as extracted. Some source pages cover other platforms; only an exact `Platform: J2ME` table is used for primary credits. |
| `download_variants_as_listed` | My Abandonware’s explicitly J2ME-scoped labels and source references. Endpoints were not fetched. |
| `source_vendor_label` | RG’s vendor field. It is not silently reclassified as developer or publisher. |
| `source_added_text` | Date added to RG. It is not a release date. |
| `source_size_value` | RG size value; the unit is unspecified in the extracted record. |
| `filenames` | Source-listed filenames, including JAR/JAD descriptor pairs. They are not separate game counts. |
| `page_sha256` | SHA-256 of the source HTML page read, not a game hash. |
| `git_blob_oid` | A Git object ID from a mirror tree; not a raw-file SHA-256. |
| `lfs_sha256_reported` | A file digest reported by the mirror when present; not independently measured. |
| `bytes_reported`, `sha1_reported`, `md5_reported` | Source-reported file inventory values, not new measurements of downloaded games. |

## Source scope

- **My Abandonware:** 989 titles explicitly listed in its J2ME directory, across 66 pages. Detail pages provide more bibliographic fields and edition labels.
- **Kahvibreak:** 5,627 rows from its public version 1.6 table. The collection includes J2ME and Mophun; the table has no per-row platform field.
- **RG-Backup:** 9,932 records in `games` and `cgames`, pinned to commit `5f610a98204c7800c6214ba1a82c44c23893b649`. Symbian and application sections are excluded. Eighty-four records have no file groups.
- **J2ME Vault:** 7,291 JAR and 111 JAD filename references from a mirror attributed by its uploader to Kahvibreak. Forty-eight Mophun files and 93 ancillary files are excluded from this site’s file inventory.
- **Internet Archive:** 25 original archive entries in `j2me-hipnosis`, extracted from item metadata.

The collections overlap. Do not add their totals together as a distinct-game count.

## Attribution and existing source notices

Full credits and links are on the site’s [source register](../sources/index.html).

RG-Backup / remixer-dec / original rugame.mobi contributors: the source README states CC BY-NC-SA 4.0. That existing notice applies to the attributed RG metadata and its reformatted display. The J2ME Vault dataset card states CC BY-NC 4.0. These notices remain specific to their respective third-party material; they do not grant permissions for Wakkatobakka’s unrelated original site code, writing, or artwork.

Original game rights and source materials retain their respective ownership. The record organization and original site presentation are maintained by Wakkatobakka.

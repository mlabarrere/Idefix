# Idéfix public corpus: dataset `v1.0.0`

A versioned, checksummed release of the data Idéfix collected from public
Telegram channels, so that anyone can rebuild the analysis **without Telegram
credentials**. What it contains, how it was collected, and the terms of use are
in the [datasheet](./DATASHEET.md). Read it before you use the data: the release
includes personal data of private individuals (the `comments` table).

| File | Role | Size | SHA-256 |
|---|---|---|---|
| `idefix-corpus-v1.0.0.dump` | PostgreSQL 17 database, `pg_dump` custom format, alembic `0008` | 45,352,794 bytes | `c2da11bbcce3f055b7f8e687e5febbbdf47bab22e82761b25abc1497c34db825` |
| `idefix-annotations-v1.0.0.tar.gz` | annotation material, extracted into `data/` | 173,339 bytes | `116dbb6f14122f5c67e8300e606367aab2ac2f6abc1eaac62a532527f4a205c2` |

Both are assets of the GitHub release
[`dataset-v1.0.0`](https://github.com/mlabarrere/Idefix/releases/tag/dataset-v1.0.0).
The authoritative description is [`manifest.json`](./manifest.json): file names,
URLs, sizes, SHA-256, row count and content checksum of every table, and the
list of what was done to the source (`sanitization`).

## 🧩 Folder layout

```text
dataset/
├── manifest.json   pinned description of the release (tracked)
├── DATASHEET.md    datasheet (Gebru et al.): composition, collection, uses, licence
├── README.md       this file
└── downloads/      fetched or locally built artefacts (gitignored)
```

## 🚀 Get it

The bootstrap does everything—download, verify, restore, pipeline, webapp:

```bash
uv run --extra embed python scripts/bootstrap.py    # all steps
uv run python scripts/bootstrap.py fetch            # only download, verify and extract
```

Without the `embed` extra, the `check` step stops unless you pass
`--skip-embeddings`.

`fetch` reads `manifest.json`, downloads each file into `dataset/downloads/`
(resumable; a file already present with the right SHA-256 is kept), checks size
and SHA-256, and extracts the archive into `data/` (no path traversal, never
overwrites a local file that differs). Two alternatives:

- `--dataset-dir PATH` copies the files from a local folder instead of
  downloading them (offline machine, pre-fetched copies);
- the environment variable `IDEFIX_DATASET_BASE_URL` (for example
  `https://mirror.example/idefix`) fetches each file from that base URL
  instead, under its release file name. The SHA-256 of the manifest still
  applies.

The `db` step then restores the dump into the local PostgreSQL of
`docker-compose.yml`, only when that database is empty.

## 🧪 Check it by hand

Download the two files from the release page into `dataset/downloads/`, then
compare with the table above (or `manifest.json`):

```bash
# Linux
sha256sum dataset/downloads/idefix-corpus-v1.0.0.dump dataset/downloads/idefix-annotations-v1.0.0.tar.gz
# macOS
shasum -a 256 dataset/downloads/idefix-corpus-v1.0.0.dump dataset/downloads/idefix-annotations-v1.0.0.tar.gz
```

```powershell
# Windows
Get-FileHash -Algorithm SHA256 dataset\downloads\idefix-corpus-v1.0.0.dump, dataset\downloads\idefix-annotations-v1.0.0.tar.gz
```

Restore without the bootstrap, into any empty PostgreSQL 17 database:

```bash
pg_restore --no-owner --no-privileges -d "$TARGET_DB" dataset/downloads/idefix-corpus-v1.0.0.dump
tar -xzf dataset/downloads/idefix-annotations-v1.0.0.tar.gz -C data
```

The restore is clean (no error). To prove that what you restored is exactly what
was released, let the release script restore the dump into a throw-away
container and compare every table with the manifest:

```bash
uv run python scripts/release_dataset.py --verify-only [--out dataset/downloads]
```

It checks size and SHA-256 of both files, runs `pg_restore` (any error fails),
then checks `alembic_version = 0008` and, for every table, the row count and the
content MD5 recorded in `manifest.json`. The checksum is
`md5(coalesce(string_agg(md5(ROW(<all columns>)::text), '' ORDER BY <primary key>), ''))`,
computed with `TimeZone=UTC`, `DateStyle='ISO, MDY'`, `IntervalStyle=postgres`,
`extra_float_digits=1`, `bytea_output=hex`; you can run it in `psql` yourself.

## 📊 What was done to the source

Nothing that changes data. The release is the complete snapshot
`idefix-supabase-post-cutover-20260618-132009` (alembic `0006`):

1. lossless restore into a fresh `postgres:17-alpine` container;
2. per-table row count and content MD5 taken **before** any change;
3. `alembic upgrade head` (`0006` → `0008`), additive only: `0007` creates the
   empty table `channel_llm_scores`, `0008` adds the nullable column
   `channel_scores.gate_families` (NULL on every row);
4. the same fingerprints recomputed on the source columns: identical for all 8
   source tables (`alembic_version` excepted—it records the upgrade);
5. `pg_dump -Fc --no-owner --no-privileges`, then a restore of that dump into a
   second database that must reproduce every fingerprint.

Two consequences worth knowing. The `channel_scores` checksum in the manifest
differs from the source one only because it now includes the (all-NULL)
`gate_families` column. And the source's hosting residue is kept as it was:
the row-level-security flag on the 9 original tables (no policy exists; a table
owner is not subject to it) and the function `public.rls_auto_enable()`.

A read-only scan searched every table and every archived file for the
collector account's secrets (`src.ingestor.session.secret_values()`): 0
occurrences. The annotation archive holds every file of `data/annotations/`
and `data/claims/` byte-for-byte.

## 🔧 Rebuild it

Maintainers only: it needs the private snapshot under `backups/` (never
published as such) and Docker.

```bash
uv run python scripts/release_dataset.py \
    --source backups/idefix-supabase-post-cutover-20260618-132009.dump \
    --version 1.0.0 --out dataset/downloads [--keep-db]
```

[`scripts/release_dataset.py`](../scripts/release_dataset.py) runs the five
steps above in a scratch container `idefix-release` bound to `127.0.0.1:55434`
(`--container`, `--port`), mounts the source read-only, builds the annotation
archive, runs the secret scan, and writes `dataset/manifest.json`. It stops
without writing a manifest when any invariant fails or the secret scan finds
anything (`--allow-secret-hits` overrides, after an explicit decision). The
container is removed at the end unless `--keep-db`.

The annotation archive is byte-reproducible (sorted members, fixed mtime taken
from the snapshot name, uid/gid 0, no gzip timestamp): the same files give the
same SHA-256. The database dump is not—`pg_dump` records its own timestamp—so a rebuilt dump has a new SHA-256 but the same per-table fingerprints. A
rebuild is therefore a new release: bump `--version`, publish the files under
the new tag, commit the new `manifest.json`.

Publishing (creating the GitHub release, uploading the assets) is a manual
maintainer step; no script here uploads anything.

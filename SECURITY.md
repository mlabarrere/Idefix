# Security policy

## 🔒 Reporting a vulnerability

> [!IMPORTANT]
> Do not open a public issue for a security problem or for anything involving
> personal data.

Report it privately through GitHub's private vulnerability reporting:
[**Security → Report a vulnerability**](https://github.com/mlabarrere/Idefix/security/advisories/new).
Only you and the maintainer can see the report.

Please include:

- a description of the problem and its impact;
- the steps to reproduce it, or a proof of concept;
- the affected commit, file, or release asset;
- a suggested fix, if you have one.

We aim to reply within 72 hours and will keep you informed until the problem
is resolved.

## 🧭 Scope

Idéfix processes data from public Telegram channels in an institutional and
operations security (OPSEC) context. These are especially critical:

- **Leaked secrets**: Supabase, Telegram, or Mistral keys and Telegram session
  strings, in the repository, its history, a release asset, or an exported
  bundle. Highest priority.
- **Personal data beyond the documented scope.** The public dataset `v1.0.0`
  deliberately contains the `comments` table: the Telegram identifier,
  username, and text of private individuals who commented in public discussion
  groups, as documented in [`dataset/DATASHEET.md`](./dataset/DATASHEET.md).
  The analyst bundle carries recurring commenters' identifiers and usernames
  (`commenters.json`). Report any personal data that goes further: comment
  text in a bundle, private content, members scraped from a group, or data
  that should have been deleted.
- **Bypassing the secret scrub** of the static export
  (`scripts/export_static.py`), or the secret scan of the dataset release
  (`scripts/release_dataset.py`).

The legal basis recorded for collecting commenters is in
`alembic/versions/0003_enrich_media_description_comments.py`.

## 🔒 Personal data and removal requests

If you are, or represent, a person whose data appears in the dataset, use the
same private channel to ask for it to be removed. A removal means a new
dataset release; the old release assets have to be withdrawn. The process is
described in [`dataset/DATASHEET.md`](./dataset/DATASHEET.md) under
Maintenance.

## 🔒 Handling secrets

- `.env*` files are ignored by git, except `.env.example`. Never commit a real
  key.
- The `detect-private-key` pre-commit hook and
  `tests/test_export_secret_scrub.py` act as safety nets.

> [!CAUTION]
> If you commit a secret by mistake, revoke or rotate it **immediately**: once
> pushed, treat it as public. Then remove it from tracking and from the history
> (`git filter-repo`), and tell the maintainer through the private channel
> above.

## 📚 Supported versions

Idéfix is a proof of concept: only the `main` branch is maintained.

| Version | Supported |
|---|---|
| `main` (currently 0.4.1) | ✅ Yes |
| Earlier tags and releases | 🔴 No |

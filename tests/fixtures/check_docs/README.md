# check_docs fixtures

Each folder is a miniature repository for one rule of `scripts/check_docs.py`:
`good/` must produce no finding for that rule, `bad/` must produce exactly the
findings listed in `tests/test_check_docs.py`. The checker excludes
`tests/fixtures/` from its own scope, so the deliberate defects here never
reach CI.

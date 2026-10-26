# Flags fixture

```bash
uv run python scripts/tool.py --dry-run -n 3 --mission gan
python scripts/tool.py --help
uv run --extra embed python scripts/tool.py run \
    --count 2
python -m pytest -x -q
python -m scripts.tool --dry-run   # same script, run as a module
python scripts/noargs.py extra positional
```

Inline: `python scripts/tool.py --mission=gan` and
`uv run python scripts/tool.py --count 1 && echo --not-a-flag`.

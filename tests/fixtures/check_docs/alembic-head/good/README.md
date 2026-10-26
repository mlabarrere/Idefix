# Alembic fixture

```
alembic/            PostgreSQL migrations (head: 0002)
```

The schema is at head `0002`. Check it:

```bash
uv run alembic current      # must print: 0002 (head)
```

The snapshot predates `0002`; migration `0001` is the baseline.

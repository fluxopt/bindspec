# Contributing

Procedure lives here. **Why** the project is shaped the way it is lives in
[README.md](README.md) and [docs/SPEC.md](docs/SPEC.md).

## Setup

```bash
uv sync
```

lpspec is not on PyPI yet, so `[tool.uv.sources]` resolves it from its repo.
That line goes away the day it publishes; the dependency floor is already
written against that day.

## The loop

```bash
uv run pytest -q
uv run ruff check --fix . && uv run ruff format .
uv run pyrefly check
```

`ruff format` runs on `.`, never on the changed `.py` files — it formats python
inside markdown too.

## The suites

| File | What it holds |
|---|---|
| `tests/test_schema.py` | the closed schema, and the near miss an unknown key gets |
| `tests/test_checking.py` | every refusal that happens **before** a source is opened |
| `tests/test_contracts.py` | every refusal that needs the data |
| `tests/test_example.py` | `examples/dispatch` end to end, through lpspec to an optimum |

The two refusal suites share a shape worth keeping: one known-good pair in
`conftest.py`, one function per mutation of it, parametrized with the mutation
as the `id`. A new check lands as a new mutation, and the unmutated pair is the
control.

## Branches, commits, PRs

Branch from `origin/main`, one topic per branch. Conventional-commit subjects
naming the problem solved — the examples are in
[AGENTS.md](AGENTS.md#commit-messages-and-pr-titles). Never force-push or delete
a branch you did not create.

## Filing issues

Say what you observed, what you expected, and the smallest bindings/model pair
that shows it. A body invalidated by a rewrite is closed and re-filed, not
annotated.

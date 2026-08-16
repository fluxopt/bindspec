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

## The narrated example

`examples/dispatch/run.py` calls the real verbs and prints what each returns.
Its whole output is committed as `run.out` and compared line for line, and the
README quotes blocks of it verbatim under a test — so a changed message fails CI
instead of leaving docs that describe an older package.

```bash
uv run python examples/dispatch/run.py               # read it
uv run pytest tests/test_example.py --update-golden  # rewrite run.out after a deliberate change
```

The diff of `run.out` is the review artifact: exactly how the story changed, in
the same PR that changed it.

## Branches, commits, PRs

Branch from `origin/main`, one topic per branch. Conventional-commit subjects
naming the problem solved — the examples are in
[AGENTS.md](AGENTS.md#commit-messages-and-pr-titles). Never force-push or delete
a branch you did not create.

## Filing issues

Say what you observed, what you expected, and the smallest bindings/model pair
that shows it. A body invalidated by a rewrite is closed and re-filed, not
annotated.

# AGENTS.md

What an agent needs on top of [CONTRIBUTING.md](CONTRIBUTING.md). What the
project *is*: [README](README.md) and [docs/SPEC.md](docs/SPEC.md).

**Part 1 is philosophy**: a change that breaks one of these is wrong here even
where it would be right elsewhere. **Part 2 is defaults**: depart from one where
the work is better served, and **say so in the PR in a sentence**, so the
exception is a decision rather than a slip.

This project is the sibling of
[lpspec](https://github.com/fluxopt/lpspec), and shares its rules deliberately.
Where a rule below is terse, that one is the long form.

# Part 1 — Philosophy

## Who is speaking

Code is checked; a discussion is trusted. Mark which is which, in every PR body,
issue and comment posted from a session:

1. **Mark generated content** at the top of the section it starts, never in a
   footer. Verbose evidence goes in `<details>`.
2. **The intent line is the human's.** Never paraphrase their ask into a
   first-person "I want this because…".
3. **Where they wrote no intent, quote the ask that defines the PR** — verbatim,
   labelled as the prompt, above the note.
4. **Do not hold the conversation.** Post marked information — a log, a diff, a
   manifest. Do not reply, concede or decide as someone else.

In the tree nothing is marked: `Co-Authored-By: Claude …` is the record.

## The line: decisions, not plumbing

**A step belongs in this package iff a reviewer would argue with it.** That is
the whole ceiling, and every scope question is decided by it.

| In | Out |
|---|---|
| what must be true of the data | reading a format |
| where a number came from, and whether it still hashes to that | fetching it |
| which coordinates exist, and in what order | inventing them |
| (later) aggregation, clustering, gap policy — the steps a methods section names | cleaning one vendor's broken export |

What is refused goes **upstream**, and its output is a pinned source. This
inverts the usual expectation of a data package, and it should: nobody reviews a
CSV reader, there are a hundred of them, and each one adopted is permanent
surface. What has no home today is the handful of steps that change the answer.

Three tripwires. Any one means the package has overbuilt:

- **It grows a plan/lowering split.** One closed schema, one polars pipeline. An
  IR of its own means it has become a second lpspec.
- **A verb is added without a study that needed it.** Parity with pandas is not
  a reason.
- **It starts owning the raw data** — a catalogue, a store, a fetch layer, a
  scheduler. Pinning is a hash, not custody.

The finish condition, so this has an end: **a stranger can re-derive a published
number from pinned inputs, and is told loudly when they cannot.**

## The dependency runs one way

bindspec imports lpspec — for `Model.to_dict()`, so the model schema has one
home — and **lpspec never imports bindspec**. A feature that would need it to is
the wrong feature, or belongs there instead.

## Simplicity is the design

- **The simplest thing that works.** No new layer, registry, config object or
  plugin seam unless something concrete needs it *now*.
- **YAGNI.** An option nobody sets, a branch nothing reaches, an abstraction
  with one caller: delete it.
- **DRY, about knowledge rather than characters.** One fact has one home. Code
  that merely *looks* alike is not duplication.

## Breaking changes are free

The project is pre-1.0 and holds no compatibility promise. Asked to change
something, change it: rename, move, delete. No alias, no deprecation cycle —
spend the effort on the load-time error instead. **A test asserting the old
behaviour is not a blocker**; say in the PR what coverage moved where.

## A claim carries its evidence

Measured numbers live in the PR that took them, beside their method and base
commit. A vague qualifier is not a conclusion. Noise is the default explanation
for a small delta.

## The tree holds facts, the PR holds the story

Rationale and alternatives go in the PR description; "previously this used
to…", "renamed from…" belong in git. Neither belongs in the code. **A construct
added, renamed or retired updates [docs/SPEC.md](docs/SPEC.md)** — §0 if it
changes a law.

## The maintainer decides

**The user merges.** An agent does not decide that work is finished. Never
force-push or delete a branch you did not create.

# Part 2 — Good defaults

## Code

- **No explanatory inline comments** — complex logic becomes a helper with a
  docstring. Kept inline: pragmas, `#:` attribute docs, and the two below.
- **Put the claim in the message that prints.** This package is almost entirely
  error messages: an error that names the offending declaration *and the
  rewrite* is the product, not a nicety.
- **A sequence of cases is parametrized, and the `id` is the label.** The
  refusal suites in `tests/` are the model: one function per mutation of a
  known-good pair, each named for what it breaks.
- **A correctness guard lands with its mutation table.** Delete each guard in
  turn, run the suite, and put the table in the PR.
- **A bug is reproduced as a strict `xfail` before it is fixed.**
- **Two comments are not explanation**: a case label where parametrizing would
  distort the test, and a one-line justification of a line that reads as a
  mistake.

## Docstrings

Google convention, checked by `ruff`'s `D` rules. **As short as it can be
without losing the reader** — and the reader of a public name is the *caller*.
A block is all or nothing: `Args:` names every parameter, or there is no block
and the summary line stands alone. The gate is `src/`; under `tests/` the `D`
rules are off.

## Commit messages and PR titles

The subject names **the problem solved**. One line, conventional-commit form, no
mechanism and no "why".

```
yes  feat(expect): a parameter can require its coordinate to be complete
yes  fix(coords): declared order survives a source that is not sorted
no   feat(expect): add covers key            ← an activity, not an outcome
no   fix(coords): use maintain_order=True    ← how it was done
```

## PR descriptions

Lead with the claim, then the evidence. Say what was verified and what you could
not check. Name what you deliberately did not do. One issue, one PR.

## Branch and worktree

One topic, one worktree, one branch, one PR. Branch from `origin/main` — the
prompt's git status is a stale snapshot.

```bash
git fetch origin
git worktree add ../wt/<topic> -b <type>/<topic> origin/main
```

Never switch the branch of the shared primary checkout. Finishing is:
committed, pushed, PR open, CI green, URL reported.

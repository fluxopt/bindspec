# bindspec

**Data that says where it came from.** The other half of
[lpspec](https://github.com/fluxopt/lpspec): that package makes the *math* an
artifact you can read, diff and review — this one does the same for the numbers
poured into it.

> [!WARNING]
> Alpha, pre-1.0. No compatibility promise, and the surface moves.

## The gap it closes

An lpspec model binds its data through a mapping of parameter names to tables.
Everything upstream of that mapping is a Python script nobody reviews, so a
reviewer can see that `p_max` came from `gen.parquet` and learn nothing about
what produced it, from what, when, or whether it is in MW.

That is where the errors actually live. Nobody ships a wrong summation; they
ship a load series missing a week, a cost in €/kWh where the model wants €/MWh,
a capacity table refreshed while the demand table was not. lpspec is
structurally unable to catch any of those — by design. Its loader checks
structure and refuses to guess at sense, so a coordinate the data never mentions
produces no rows, and the model that comes out is feasible, cheaper and wrong.

`bindings.yaml` is where you say what must be true, and the manifest is what
comes back.

## The file

```yaml
sources:
  generators:
    path: data/generators.csv
    sha256: 4f1a…                  # enforced when present, recorded when absent
    units: {p_max_mw: MW, marginal_cost: EUR/MWh}
  demand:
    path: data/demand.csv
    units: {mw: MW}

coords:                            # master coordinates, in their declared order
  snapshot: {from: demand, column: hour}

bind:
  p_max: {from: generators, dims: {generator: name}, value: p_max_mw}
  cost:  {from: generators, dims: {generator: name}, value: marginal_cost}
  load:  {from: demand, dims: {snapshot: hour}, value: mw}

expect:
  p_max: {units: MW, range: [0, null], covers: generator}
  load:  {units: MW, covers: snapshot}
```

```python
import bindspec as bs
import lpspec as lps

binding = bs.bind('bindings.yaml', 'model.yaml')
result = lps.solve('model.yaml', binding.sources)
binding.write_manifest('manifest.json')
```

Two verbs. `bs.check(bindings, model)` decides everything that can be decided
without opening a source — every declared parameter bound exactly once, every
dim set equal, every dimension's members declared somewhere — and `bs.bind`
does that, then reads, then checks the data against `expect:`.

```bash
bindspec check bindings.yaml model.yaml
bindspec manifest bindings.yaml model.yaml -o manifest.json
```

## What comes back

[examples/dispatch](examples/dispatch) runs end to end — `uv run python
examples/dispatch/run.py` — and its whole output is committed as
[`run.out`](examples/dispatch/run.out) and asserted line for line, so nothing
quoted on this page can go stale unnoticed.

What the bind reports, per parameter and per coordinate:

```text
[2] bind -- read, then check what was read
    p_max      3 rows  MW        keyed, units, non_null, range, covers:generator
    cost       3 rows  EUR/MWh   keyed, units, non_null, range, covers:generator
    load       6 rows  MW        keyed, units, non_null, covers:snapshot
    snapshot   6 members, from the bindings
    generator  3 members, from the model
```

What a reader needs to re-derive the answer — the path as *declared*, so the
record still means something on somebody else's checkout:

```text
      "sources": {
        "demand": {
          "bytes": 55,
          "path": "data/demand.csv",
          "sha256": "3997994d9c84db4f6b4629239d257bc43150e372413ba7c43ccbbb993b2e7998"
        },
```

And a refusal, naming the parameter, what was expected and what to do:

```text
      ContractError: parameter 'p_max' covers 'generator', and 1 of its 3 members has no row: 'gas'.
```

That last one is the argument for the package in one line. Without it lpspec
builds that model, solves it, and hands back a cheaper answer.

## What it checks

| Always | Because |
|---|---|
| the dims key the rows | two rows for one coordinate is a doubled coefficient downstream, never a modelling choice |
| no null values | switch it off per parameter with `non_null: false` to bind them as absent rows |
| every dimension has declared members | leaving them to be derived costs the declared order, which `shift` reads positionally |
| the bindings and the model agree | before a byte is read |
| a pinned source still hashes to its pin | a study you cannot re-derive is a number without evidence |

| On declaration | Spelling |
|---|---|
| units | `units: MW` — compared verbatim against the source's, never converted |
| bounds | `range: [0, null]` |
| coverage | `covers: snapshot`, a list, or `true` for every dim of the parameter |

## What it will not do

The line is **decisions, not plumbing**: a step belongs here if a reviewer would
argue with it.

| Refused | Instead |
|---|---|
| format adapters, API clients, scraping | produce the file upstream; pin it here |
| cleaning one vendor's broken export | the same — nobody reviews a CSV reader |
| unit *conversion* | convert upstream and declare what you produced |
| a transform language | deferred until the contracts say which transforms are worth recording — [SPEC](docs/SPEC.md#9-what-is-not-here-yet) |

It is not a workflow engine, not dbt, not a units library and not a catalogue.
Pinning is a hash; it is not custody.

## Install

```bash
pip install bindspec
```

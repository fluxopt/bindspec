# SPEC

What a `bindings.yaml` may contain and what it means. The companion is
[lpspec's SPEC](https://github.com/fluxopt/lpspec/blob/main/docs/SPEC.md), whose
§8 is the seam this file sits on.

## 0. The laws

| # | Law | § |
|---|---|---|
| 1 | Four declaration keys plus `version` and `description`, and **the schema is closed at every level** — an unknown key is a load error naming the near miss. | [§1](#1-file-shape) |
| 2 | **Everything decidable without a source is decided without one.** | [§6](#6-what-is-decided-when) |
| 3 | **Every declared parameter is bound exactly once**, and every bound name is declared. The model is the source of truth about what exists. | [§4](#4-bind) |
| 4 | **Every dimension's members are declared** — by the model's `values:` or by `coords:`, never both and never neither. | [§3](#3-coords) |
| 5 | **The dims key the rows.** Not a declaration, not optional. | [§5](#5-expect) |
| 6 | **Units are compared, never converted**, and verbatim: a unit is a spelling, not a parsed quantity. | [§5](#5-expect) |
| 7 | **A pin is enforced or it is recorded.** Either way the manifest carries the digest that was read. | [§2](#2-sources) |

## 1. File shape

Four declaration keys — `sources`, `coords`, `bind`, `expect` — plus `version`
and `description`.

`description` says what this instance *is*, in prose, and is never parsed. A
bindings file describes one binding of one model, so "six hours of the 2023
fleet, as exported from the planning sheet" is the sentence that belongs here.

`version` declares which surface the file targets; absent means `0`, and `0`
means unstable. A version this reader does not know is a load error and nothing
else — it gates no behaviour, because keeping two surfaces alive costs more than
the error costs.

An unrecognised key at any level is refused with the near miss
(`unknown key 'unit' at sources.demand. Did you mean 'units'?`). Ignoring it
would let a typo change what is checked, and a dropped `expect` entry is a
contract silently not held.

## 2. `sources`

An external file, by name.

```yaml
sources:
  demand:
    path: data/demand.csv
    sha256: 4f1a…
    units: {mw: MW}
```

- **`path`** resolves against the directory holding the bindings file, or the
  working directory when a dict is passed instead of a path. `.parquet` and
  `.csv` are read; any other suffix is refused by name.
- **`sha256`** is enforced when present and recorded when absent. A mismatch
  refuses the bind rather than warning: the pin exists so that a number can be
  re-derived, and a pin that yields is not one.
- **`units`** maps a *column* to its unit, verbatim.

A source may feed any number of parameters and coordinates. It is a file, not a
parameter — which is why it is a separate key from `bind`.

## 3. `coords`

Where a dimension's members come from, and in what order.

```yaml
coords:
  snapshot: {from: demand, column: hour}
```

Order is order of first appearance in the column, deduplicated — the same rule
lpspec applies to a coordinate table in `sources` (its §8, precedence 1), and
the reason this key exists at all. Left to lpspec's step 4, a dimension is
derived from the parameter tables as *sorted* distinct values, which costs the
declared order that `shift` reads positionally and pays for a full scan of every
parameter carrying the dim.

So bindspec refuses the derivation: **every dimension must have declared
members**, from the model's own `values:` or from here. Declaring in both places
is equally an error — two sources of truth for one fact.

## 4. `bind`

One model parameter, drawn from one source.

```yaml
bind:
  load: {from: demand, dims: {snapshot: hour}, value: mw}
```

`dims` maps each of the parameter's **model** dimensions to the **source**
column carrying it, and `value` names the column carrying the number. The
mapping is renaming and nothing else: no expression, no cast, no derived column.

The dim set must *equal* what the model declares for that parameter — not
contain it, not be contained by it.

## 5. `expect`

What must hold of the data once it is read. A parameter with no entry is still
checked against the defaults, so `non_null` holds everywhere it is not switched
off.

| Key | Default | Meaning |
|---|---|---|
| `units` | none | The source must declare this exact spelling for the value column. |
| `range` | none | Inclusive `[low, high]`; either end may be `null`. |
| `covers` | `false` | A dim, a list of dims, or `true` for all of the parameter's — every master coordinate member must have a row. |
| `non_null` | `true` | A null in the value column is refused. |

**Units are compared verbatim.** `MW` and `megawatt` are different units here,
and `kW` against `MW` is an error rather than a factor of a thousand. Parsing
them would mean owning a dimensional algebra and a registry of spellings; the
whole value of the check is that the two declarations came from different people
and have to agree.

Because both sides of that comparison *are* declarations, it is settled before a
source is opened — §6 — and refused as a `BindingError` rather than a
`ContractError`. It is the one entry in this section that never reads a byte.

**Coverage is the check the engine cannot make.** lpspec is right not to: sparse
data gives sparse variables, and a missing row is how absence is *said*. `covers`
is where you say this parameter is not one of those.

**Keys are checked unconditionally.** Two rows sharing a coordinate is never a
modelling choice, and downstream it is a doubled coefficient rather than an
error.

## 6. What is decided when

Before any source is opened: the schema, every name (parameter, source,
dimension), every dim set, every dimension's members, and every expectation that
can be refuted structurally — `covers` naming a foreign dim, and `units` either
expected of a column whose source declares none or expected as a spelling the
source contradicts.

After reading: the pin of §2, and the contracts of §5 that need values — keys,
nulls, range, coverage.

## 7. What is deliberately not checked

- **That a value is plausible.** `range` is the place to say so.
- **Dtypes.** lpspec's loader coerces and raises on what it cannot; a second
  copy of that rule here would drift from it.
- **That coordinates outside the master index are absent.** lpspec refuses those
  by design, with a better message than this package could give.

## 8. The manifest

What `bind` records, and what `write_manifest` puts on disk. It is the output
half of this file: `bindings.yaml` says what must be true, and the manifest says
what was read and what held.

```json
"sources": {"demand": {"path": "data/demand.csv", "sha256": "3997…", "bytes": 55}},
"coords":  {"snapshot": {"members": 6, "from": "bindings", "source": "demand", "column": "hour"}},
"parameters": {"load": {"source": "demand", "column": "mw", "rows": 6, "units": "MW",
                        "checked": ["keyed", "units", "non_null", "covers:snapshot"]}}
```

Two properties it is built to have, and both are load-bearing:

- **A path is recorded as declared, never as resolved.** An absolute path off
  one laptop re-derives nothing on anybody else's checkout, and re-deriving is
  the only reason the record exists. The digest is the identity; the path is a
  locator relative to the bindings file.
- **It is deterministic.** No timestamps, no iteration order, no version of this
  package baked into a value. The same bytes produce the same record, so two
  runs are comparable by `diff` and a manifest can be committed beside a result.

`checked` lists what *held*, not what was declared — which is why a parameter
with no `expect:` entry still shows `keyed` and `non_null`.

The full worked example is [`examples/dispatch/run.out`](../examples/dispatch/run.out).

## 9. What is not here yet

**Transforms.** Resampling, clustering and aggregation change an answer more
than most constraints do, and recording only their *output* pins the model
without pinning the study. They are in scope for that reason and no other — as
the closure of provenance, never as a data-manipulation feature — and the verb
set will be derived from what real bindings do between a raw file and a
parameter rather than designed up front.

**Streaming hand-off.** A bound parameter is materialised as a frame today.
Handing lpspec a path, so its own scan stays the only pass over the data, is the
version that keeps its memory claim intact; it waits on a measurement rather
than a guess about which shape is worth the cache directory.

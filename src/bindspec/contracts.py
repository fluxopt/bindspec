"""The checks that need the data, and the one that is not optional.

lpspec's loader deliberately checks structure and not sense: a coordinate its
data never mentions produces no rows, and sparse data gives sparse variables
(SPEC §8). That is right for an engine which must not guess, and it leaves a
model that is feasible, cheaper and wrong when a week of load goes missing.
These are the assertions that close it.

Duplicate keys are refused unconditionally rather than by declaration: two rows
for one coordinate is never a modelling choice, and downstream it is a doubled
coefficient rather than an error.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import polars as pl

from bindspec.errors import ContractError

if TYPE_CHECKING:
    from collections.abc import Sequence

    from bindspec.schema import Expect


def _check_keys(name: str, frame: pl.DataFrame, dims: Sequence[str]) -> None:
    if not dims:
        if frame.height != 1:
            raise ContractError(
                f"parameter '{name}' has no dims, so its source must hold one row; it holds {frame.height}."
            )
        return
    keys = frame.select(dims).n_unique()
    if keys != frame.height:
        duplicated = (
            frame.select(dims).filter(pl.struct(dims).is_duplicated()).unique(maintain_order=True).head(3).rows()
        )
        raise ContractError(
            f"parameter '{name}' has {frame.height - keys} row(s) sharing a coordinate with another; "
            f'[{", ".join(dims)}] must key the rows. First duplicated: {duplicated}.'
        )


def _check_nulls(name: str, frame: pl.DataFrame, expect: Expect) -> None:
    nulls = frame['value'].null_count()
    if nulls and expect.non_null:
        raise ContractError(
            f"parameter '{name}' has {nulls} null value(s). Fill them upstream, or declare non_null: false "
            'to bind them as absent rows.'
        )


def _check_range(name: str, frame: pl.DataFrame, expect: Expect) -> None:
    if expect.range is None or frame.is_empty():
        return
    low, high = expect.range
    found_low, found_high = frame['value'].min(), frame['value'].max()
    if not isinstance(found_low, int | float) or not isinstance(found_high, int | float):
        raise ContractError(
            f"parameter '{name}' declares a range, and its value column is {frame['value'].dtype}, "
            'which has no ordering against a number.'
        )
    if low is not None and found_low < low:
        raise ContractError(f"parameter '{name}' expects values >= {low}; the lowest is {found_low}.")
    if high is not None and found_high > high:
        raise ContractError(f"parameter '{name}' expects values <= {high}; the highest is {found_high}.")


def _aligned(name: str, dim: str, master: pl.DataFrame, frame: pl.DataFrame) -> pl.DataFrame:
    """The master coordinate, in the dtype the parameter carries the dim as.

    A join needs one type where the set comparison this replaced did not, and a
    dim declared by ``values:`` in the model gets whatever polars infers from
    python literals — so Int64 ``[0, 1, 2]`` against an Int32 column has to be
    brought together rather than reported as wholly missing. Only a same-kind
    cast is allowed: polars will happily turn ``0`` into ``'0'``, and silently
    agreeing that those are the same coordinate is worse than refusing.
    """
    declared, carried = master.schema[dim], frame.schema[dim]
    if declared == carried:
        return master
    same_kind = (declared.is_numeric() and carried.is_numeric()) or (declared.is_temporal() and carried.is_temporal())
    if not same_kind:
        raise ContractError(
            f"parameter '{name}' carries '{dim}' as {carried}, and the master coordinate is {declared}. "
            'Those are different kinds of value, so coverage cannot be checked.'
        )
    try:
        return master.with_columns(pl.col(dim).cast(carried))
    except pl.exceptions.PolarsError as error:
        raise ContractError(
            f"parameter '{name}' carries '{dim}' as {carried}, which does not hold every member of the "
            f'master coordinate ({declared}).'
        ) from error


def _check_coverage(
    name: str, frame: pl.DataFrame, expect: Expect, dims: Sequence[str], coords: dict[str, pl.DataFrame]
) -> None:
    for dim in expect.covered(tuple(dims)):
        master = _aligned(name, dim, coords[dim], frame)
        missing = (
            master.with_row_index('_position').join(frame.select(dim).unique(), on=dim, how='anti').sort('_position')
        )
        if missing.height:
            shown = ', '.join(repr(value) for value in missing[dim].head(5).to_list())
            more = f' (+{missing.height - 5} more)' if missing.height > 5 else ''
            raise ContractError(
                f"parameter '{name}' covers '{dim}', and {missing.height} of its {master.height} members "
                f'{"has" if missing.height == 1 else "have"} no row: {shown}{more}.'
            )


def check_parameter(
    name: str,
    frame: pl.DataFrame,
    dims: Sequence[str],
    expect: Expect,
    coords: dict[str, pl.DataFrame],
) -> list[str]:
    """Run every contract that applies to one bound parameter.

    ``units`` is absent here on purpose: comparing two declarations needs no
    data, so :mod:`bindspec.checking` has already settled it.

    Args:
        name: The parameter's name, as it appears in the model.
        frame: Its rows, columns ``(dims…, value)``, already renamed.
        dims: The parameter's dimensions, in the model's declared order.
        expect: What was declared about it, or the defaults.
        coords: Master coordinate members by dimension, one single-column frame
            each, for coverage.

    Returns:
        The names of the checks that held, for the manifest.

    Raises:
        ContractError: On the first expectation that does not hold. The message
            names the parameter, what was expected and what was found.
    """
    _check_keys(name, frame, dims)
    _check_nulls(name, frame, expect)
    _check_range(name, frame, expect)
    _check_coverage(name, frame, expect, dims, coords)

    ran = ['keyed']
    if expect.units is not None:
        ran.append('units')
    if expect.non_null:
        ran.append('non_null')
    if expect.range is not None:
        ran.append('range')
    ran.extend(f'covers:{dim}' for dim in expect.covered(tuple(dims)))
    return ran

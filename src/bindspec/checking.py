"""Everything decidable before a source is opened, decided there.

The model says which parameters exist, over which dimensions; the bindings say
where each one comes from. Those two facts settle most of what can go wrong, and
settling it here means a typo costs a load error rather than a scan of a file
that was never going to satisfy anything.
"""

from __future__ import annotations

import difflib
from typing import TYPE_CHECKING, Any

from bindspec.errors import BindingError

if TYPE_CHECKING:
    from bindspec.schema import Bindings


def _near(name: str, candidates: list[str]) -> str:
    match = difflib.get_close_matches(name, candidates, n=1, cutoff=0.6)
    return f" Did you mean '{match[0]}'?" if match else ''


def _parameter_dims(model: dict[str, Any], name: str) -> tuple[str, ...]:
    return tuple(model['parameters'][name].get('dims') or ())


def _check_names(spec: Bindings, model: dict[str, Any]) -> None:
    declared = list(model.get('parameters') or {})
    for name in spec.bind:
        if name not in declared:
            raise BindingError(
                f"bind names '{name}', which the model does not declare as a parameter.{_near(name, declared)}"
            )
    if missing := [name for name in declared if name not in spec.bind]:
        raise BindingError(
            f'the model declares parameters no binding supplies: {", ".join(missing)}. '
            'Every declared parameter must be bound exactly once.'
        )


def _check_dims(spec: Bindings, model: dict[str, Any]) -> None:
    for name, bind in spec.bind.items():
        declared, bound = _parameter_dims(model, name), tuple(bind.dims)
        if set(declared) != set(bound):
            raise BindingError(
                f"parameter '{name}' is declared over [{', '.join(declared)}] "
                f'and bound over [{", ".join(bound)}]. The dim sets must be equal.'
            )


def _check_sources(spec: Bindings) -> None:
    known = list(spec.sources)
    for name, bind in spec.bind.items():
        if bind.from_ not in known:
            raise BindingError(
                f"bind '{name}' reads source '{bind.from_}', which is not declared.{_near(bind.from_, known)}"
            )
    for dim, coordinate in spec.coords.items():
        if coordinate.from_ not in known:
            raise BindingError(
                f"coords '{dim}' reads source '{coordinate.from_}', which is not declared.{_near(coordinate.from_, known)}"
            )


def _check_coords(spec: Bindings, model: dict[str, Any]) -> None:
    dimensions = model.get('dimensions') or {}
    for dim in spec.coords:
        if dim not in dimensions:
            raise BindingError(
                f"coords names '{dim}', which the model does not declare as a dimension.{_near(dim, list(dimensions))}"
            )
        if dimensions[dim].get('values') is not None:
            raise BindingError(
                f"dimension '{dim}' takes its members from the model's own values:, so coords must not supply them too. "
                'Drop one of the two — whichever is not the source of truth.'
            )
    for dim, declaration in dimensions.items():
        if dim not in spec.coords and declaration.get('values') is None:
            raise BindingError(
                f"dimension '{dim}' has no declared members: add it to coords:, or give the model a values: list. "
                'Leaving it to be derived from the parameter tables costs the declared order, which shift reads positionally.'
            )


def _check_expectations(spec: Bindings, model: dict[str, Any]) -> None:
    for name, expect in spec.expect.items():
        if name not in spec.bind:
            raise BindingError(f"expect names '{name}', which is not bound.{_near(name, list(spec.bind))}")
        dims = _parameter_dims(model, name)
        for dim in expect.covered(dims):
            if dim not in dims:
                raise BindingError(f"expect '{name}' covers '{dim}', which is not one of its dims [{', '.join(dims)}].")
        if expect.units is not None:
            bind = spec.bind[name]
            declared = spec.sources[bind.from_].units
            if bind.value not in declared:
                raise BindingError(
                    f"expect '{name}' requires unit '{expect.units}', but source '{bind.from_}' declares no unit "
                    f"for column '{bind.value}'. Add it under that source's units:, or drop the expectation."
                )
            if declared[bind.value] != expect.units:
                raise BindingError(
                    f"parameter '{name}' expects unit '{expect.units}', and source '{bind.from_}' declares "
                    f"'{declared[bind.value]}' for column '{bind.value}'. Units are compared verbatim and never "
                    'converted — convert upstream and declare what you produced.'
                )


def check_structure(spec: Bindings, model: dict[str, Any]) -> None:
    """Refuse a bindings/model pair that cannot work, without reading anything.

    Args:
        spec: The parsed bindings.
        model: The model as data — what ``lpspec.Model.to_dict()`` returns.

    Raises:
        BindingError: If a name, a dim set, a coordinate or an expectation does
            not line up. The message names the offending declaration and the
            rewrite.
    """
    _check_names(spec, model)
    _check_dims(spec, model)
    _check_sources(spec)
    _check_coords(spec, model)
    _check_expectations(spec, model)

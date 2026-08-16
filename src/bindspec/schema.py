"""The `bindings.yaml` surface, closed at every level.

What each key means is [SPEC](../../docs/SPEC.md). This module is the shape and
nothing else: no file is opened here, no model is consulted, and a document that
parses may still be refused by :mod:`bindspec.checking`.
"""

from __future__ import annotations

import difflib
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from bindspec.errors import SchemaError

#: The only language version this reader understands.
KNOWN_VERSIONS = (0,)


class _Closed(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True, populate_by_name=True)


class Source(_Closed):
    """An external file, optionally pinned to the bytes it had when this was written.

    Attributes:
        path: Location, resolved against the directory holding the bindings file.
        sha256: Enforced when present, recorded in the manifest when absent.
        units: Column name to its unit, verbatim. Compared, never converted.
    """

    path: str
    sha256: str | None = None
    units: dict[str, str] = Field(default_factory=dict)


class Coordinate(_Closed):
    """Where a dimension's members come from, and in what order.

    Attributes:
        from_: Name of a declared source.
        column: Column carrying the members. First occurrence of a value is its position.
    """

    from_: str = Field(alias='from')
    column: str


class Bind(_Closed):
    """One model parameter, drawn from one source.

    Attributes:
        from_: Name of a declared source.
        dims: Model dimension to the column carrying it. Renaming only.
        value: Column carrying the parameter's value.
    """

    from_: str = Field(alias='from')
    dims: dict[str, str] = Field(default_factory=dict)
    value: str


class Expect(_Closed):
    """What must hold of a bound parameter's data.

    An unlisted parameter is checked against the defaults below, so ``non_null``
    holds everywhere it is not switched off.

    Attributes:
        units: Required unit of the value column, compared verbatim to the source's.
        range: Inclusive ``[low, high]``; either end may be null for unbounded.
        covers: Dimensions whose master coordinate must be complete in this
            parameter — a name, a list, or ``true`` for all of its dims.
        non_null: Whether a null in the value column is refused.
    """

    units: str | None = None
    range: tuple[float | None, float | None] | None = None
    covers: bool | str | list[str] = False
    non_null: bool = True

    def covered(self, dims: tuple[str, ...]) -> tuple[str, ...]:
        """The dimensions ``covers`` names, given the parameter's declared dims."""
        if self.covers is True:
            return dims
        if self.covers is False:
            return ()
        if isinstance(self.covers, str):
            return (self.covers,)
        return tuple(self.covers)


class Bindings(_Closed):
    """A whole bindings file, parsed and shape-checked.

    Attributes:
        version: Which surface the file is written against.
        description: What this instance is. Never parsed.
        sources: External files by name.
        coords: Master coordinates this file supplies, by dimension.
        bind: Model parameters, by name.
        expect: Contracts, by parameter name.
        directory: Where relative paths resolve, set by :func:`load_bindings`.
    """

    version: int = 0
    description: str | None = None
    sources: dict[str, Source] = Field(default_factory=dict)
    coords: dict[str, Coordinate] = Field(default_factory=dict)
    bind: dict[str, Bind] = Field(default_factory=dict)
    expect: dict[str, Expect] = Field(default_factory=dict)
    directory: Path = Path()

    @field_validator('version')
    @classmethod
    def _known_version(cls, value: int) -> int:
        if value not in KNOWN_VERSIONS:
            raise ValueError(f'bindings declare version {value}, and this reader understands {list(KNOWN_VERSIONS)}')
        return value


#: Which model a nesting level is validated against, for the near-miss suggestion.
_SECTIONS = {'sources': Source, 'coords': Coordinate, 'bind': Bind, 'expect': Expect}


def _suggest(key: str, candidates: list[str]) -> str:
    near = difflib.get_close_matches(key, candidates, n=1, cutoff=0.6)
    return f" Did you mean '{near[0]}'?" if near else f' Known keys: {", ".join(sorted(candidates))}.'


def _schema_error(error: ValidationError) -> SchemaError:
    first = error.errors()[0]
    where = '.'.join(str(part) for part in first['loc'])
    if first['type'] != 'extra_forbidden':
        return SchemaError(f'{where}: {first["msg"]}')
    key = str(first['loc'][-1])
    section = _SECTIONS.get(str(first['loc'][0])) if len(first['loc']) > 1 else Bindings
    known = [field.alias or name for name, field in (section or Bindings).model_fields.items() if name != 'directory']
    return SchemaError(f"unknown key '{key}' at {where}.{_suggest(key, known)}")


def load_bindings(source: str | Path | dict[str, Any]) -> Bindings:
    """Parse a bindings file, or a dict already holding one.

    Args:
        source: Path to a YAML file, or the mapping it would have parsed to.
            Relative source paths resolve against the file's directory, or the
            working directory when a dict is passed.

    Returns:
        The parsed document. Nothing has been read and no model consulted.

    Raises:
        SchemaError: If a key is unknown, a value has the wrong type, or the
            declared version is one this reader does not understand.
    """
    if isinstance(source, dict):
        document, directory = dict(source), Path()
    else:
        path = Path(source)
        document, directory = yaml.safe_load(path.read_text()) or {}, path.parent
    try:
        return Bindings.model_validate(document | {'directory': directory})
    except ValidationError as error:
        raise _schema_error(error) from None

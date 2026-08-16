"""Read the sources, check them, and hand out the mapping lpspec takes."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import polars as pl

from bindspec.checking import check_structure
from bindspec.contracts import check_parameter
from bindspec.errors import SourceError
from bindspec.schema import Bindings, Expect, load_bindings

_READERS = {'.parquet': pl.scan_parquet, '.csv': pl.scan_csv}


@dataclass(frozen=True)
class Binding:
    """A model's data, read and checked.

    Attributes:
        sources: What to pass to ``lpspec.solve`` — one entry per parameter, plus
            one per dimension this file supplies members for.
        manifest: What was read and what held: a digest per source, a row count
            and check list per parameter, coordinate sizes. Deterministic, so two
            runs over the same bytes produce the same record.
    """

    sources: dict[str, Any]
    manifest: dict[str, Any] = field(default_factory=dict)

    def write_manifest(self, path: str | Path) -> Path:
        """Write the manifest as JSON, keys sorted, and return where it went."""
        import json

        target = Path(path)
        target.write_text(json.dumps(self.manifest, indent=2, sort_keys=True, default=str) + '\n')
        return target


def _digest(path: Path) -> str:
    sha = hashlib.sha256()
    with path.open('rb') as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b''):
            sha.update(chunk)
    return sha.hexdigest()


def _scan(path: Path) -> pl.LazyFrame:
    reader = _READERS.get(path.suffix)
    if reader is None:
        raise SourceError(f"cannot read '{path}': bindspec reads {', '.join(sorted(_READERS))}, not '{path.suffix}'.")
    if not path.exists():
        raise SourceError(f'source file does not exist: {path}')
    return reader(path)


def _resolve(spec: Bindings) -> dict[str, dict[str, Any]]:
    resolved: dict[str, dict[str, Any]] = {}
    for name, source in spec.sources.items():
        path = spec.directory / source.path
        scan = _scan(path)
        digest = _digest(path)
        if source.sha256 is not None and digest != source.sha256:
            raise SourceError(
                f"source '{name}' is pinned to {source.sha256[:12]}… and {path} hashes to {digest[:12]}…. "
                'The file changed since the pin was written: re-pin it deliberately, or restore the bytes.'
            )
        resolved[name] = {'scan': scan, 'path': path, 'sha256': digest, 'bytes': path.stat().st_size}
    return resolved


def _coordinates(
    spec: Bindings, model: dict[str, Any], resolved: dict[str, dict[str, Any]]
) -> tuple[dict[str, pl.DataFrame], dict[str, list[Any]]]:
    frames: dict[str, pl.DataFrame] = {}
    members: dict[str, list[Any]] = {}
    for dim, declaration in (model.get('dimensions') or {}).items():
        if declaration.get('values') is not None:
            members[dim] = list(declaration['values'])
            continue
        coordinate = spec.coords[dim]
        scan = resolved[coordinate.from_]['scan']
        frame = scan.select(pl.col(coordinate.column).alias(dim)).unique(maintain_order=True).collect()
        frames[dim] = frame
        members[dim] = frame[dim].to_list()
    return frames, members


def bind(bindings: str | Path | dict[str, Any], model: Any) -> Binding:
    """Read a model's data, check every contract, and record what was read.

    Args:
        bindings: Path to a bindings file, or the mapping it would parse to.
        model: The model the data is for — anything with ``to_dict()``
            (an ``lpspec.Model``), a path to its YAML, or that dict.

    Returns:
        A :class:`Binding` whose ``sources`` goes straight to ``lpspec.solve``.

    Raises:
        SchemaError: If the bindings file is not one.
        BindingError: If the bindings and the model disagree.
        SourceError: If a source is unreadable, or is not the bytes it was pinned to.
        ContractError: If the data does not satisfy what was declared about it.
    """
    spec = load_bindings(bindings)
    declared = _as_dict(model)
    check_structure(spec, declared)

    resolved = _resolve(spec)
    coordinate_frames, members = _coordinates(spec, declared, resolved)
    sources: dict[str, Any] = dict(coordinate_frames)
    parameters: dict[str, Any] = {}

    for name, plan in spec.bind.items():
        dims = tuple(declared['parameters'][name].get('dims') or ())
        frame = (
            resolved[plan.from_]['scan']
            .select(
                *(pl.col(plan.dims[dim]).alias(dim) for dim in dims),
                pl.col(plan.value).alias('value'),
            )
            .collect()
        )
        expect = spec.expect.get(name, Expect())
        units = spec.sources[plan.from_].units.get(plan.value)
        ran = check_parameter(name, frame, dims, expect, members)
        sources[name] = frame
        parameters[name] = {
            'source': plan.from_,
            'column': plan.value,
            'rows': frame.height,
            'units': units,
            'checked': ran,
        }

    return Binding(sources=sources, manifest=_manifest(spec, resolved, coordinate_frames, members, parameters))


def _manifest(
    spec: Bindings,
    resolved: dict[str, dict[str, Any]],
    coordinate_frames: dict[str, pl.DataFrame],
    members: dict[str, list[Any]],
    parameters: dict[str, Any],
) -> dict[str, Any]:
    return {
        'description': spec.description,
        'version': spec.version,
        'sources': {
            name: {'path': spec.sources[name].path, 'sha256': entry['sha256'], 'bytes': entry['bytes']}
            for name, entry in resolved.items()
        },
        'coords': {
            dim: {
                'members': len(values),
                'from': 'bindings' if dim in coordinate_frames else 'model',
                **(
                    {'source': spec.coords[dim].from_, 'column': spec.coords[dim].column}
                    if dim in coordinate_frames
                    else {}
                ),
            }
            for dim, values in members.items()
        },
        'parameters': parameters,
    }


def _as_dict(model: Any) -> dict[str, Any]:
    if hasattr(model, 'to_dict'):
        return model.to_dict()
    if isinstance(model, dict):
        return model
    import lpspec

    return lpspec.load_model(model).to_dict()


def check(bindings: str | Path | dict[str, Any], model: Any) -> None:
    """Refuse a bindings/model pair that cannot work, without reading a source.

    Args:
        bindings: Path to a bindings file, or the mapping it would parse to.
        model: The model the data is for, in any form :func:`bind` accepts.

    Raises:
        SchemaError: If the bindings file is not one.
        BindingError: If the bindings and the model disagree.
    """
    check_structure(load_bindings(bindings), _as_dict(model))

"""Data that says where it came from, for models written in lpspec.

The math is the YAML file lpspec reads; this package is the other half — which
bytes filled it, what was checked about them, and a record either can be
reproduced from.

    import bindspec as bs
    import lpspec as lps

    binding = bs.bind('bindings.yaml', 'model.yaml')
    result = lps.solve('model.yaml', binding.sources)
    binding.write_manifest('manifest.json')
"""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError as _PackageNotFoundError
from importlib.metadata import version as _installed_version

from bindspec.binding import Binding, bind, check
from bindspec.errors import BindingError, BindspecError, ContractError, SchemaError, SourceError
from bindspec.schema import Bindings, load_bindings

__all__ = [
    'Binding',
    'BindingError',
    'Bindings',
    'BindspecError',
    'ContractError',
    'SchemaError',
    'SourceError',
    'bind',
    'check',
    'load_bindings',
]

try:
    __version__ = _installed_version('bindspec')
except _PackageNotFoundError:
    __version__ = '0.0.0'

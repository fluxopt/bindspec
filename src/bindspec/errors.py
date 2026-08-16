"""The exception tree. Every failure this package raises is one of these."""

from __future__ import annotations


class BindspecError(Exception):
    """Root of every error raised by bindspec."""


class SchemaError(BindspecError):
    """The bindings file is not a bindings file — an unknown key, a bad type."""


class BindingError(BindspecError):
    """The bindings and the model disagree, decidable before any source is read."""


class SourceError(BindspecError):
    """A source could not be read, or its bytes are not the bytes that were pinned."""


class ContractError(BindspecError):
    """Data was read and a declared expectation does not hold of it."""

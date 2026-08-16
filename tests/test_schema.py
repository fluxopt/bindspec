from __future__ import annotations

import pytest

from bindspec import SchemaError, load_bindings


def test_an_unknown_top_level_key_names_the_near_miss():
    with pytest.raises(SchemaError) as raised:
        load_bindings({'sourcs': {}})
    assert "Did you mean 'sources'?" in str(raised.value), 'a mistyped section suggests the one it nearly is'


def test_an_unknown_key_inside_a_binding_names_where_it_was():
    with pytest.raises(SchemaError) as raised:
        load_bindings({'bind': {'p_max': {'from': 'gen', 'value': 'cap', 'dim': {}}}})
    message = str(raised.value)
    assert 'bind.p_max.dim' in message, 'the location is the path to the key, not just the key'
    assert "Did you mean 'dims'?" in message


def test_a_version_this_reader_does_not_know_is_refused():
    with pytest.raises(SchemaError, match='version 1'):
        load_bindings({'version': 1})


def test_from_is_spelled_from():
    spec = load_bindings({'sources': {'gen': {'path': 'g.csv'}}, 'bind': {'p': {'from': 'gen', 'value': 'v'}}})
    assert spec.bind['p'].from_ == 'gen', '`from` is a python keyword, so the field is from_ and the key stays `from`'

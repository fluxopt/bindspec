from __future__ import annotations

import copy
import re

import pytest

from bindspec import BindingError, check
from tests.conftest import MODEL


def rename_bound(spec: dict) -> dict:
    spec['bind']['p_maks'] = spec['bind'].pop('p_max')
    return spec


def drop_a_binding(spec: dict) -> dict:
    del spec['bind']['load']
    return spec


def wrong_dims(spec: dict) -> dict:
    spec['bind']['p_max']['dims'] = {'snapshot': 'name'}
    return spec


def unknown_source(spec: dict) -> dict:
    spec['bind']['p_max']['from'] = 'genn'
    return spec


def unknown_dimension(spec: dict) -> dict:
    spec['coords']['snapshoot'] = spec['coords'].pop('snapshot')
    return spec


def coords_for_a_model_declared_dim(spec: dict) -> dict:
    spec['coords']['generator'] = {'from': 'gen', 'column': 'name'}
    return spec


def no_members_anywhere(spec: dict) -> dict:
    del spec['coords']['snapshot']
    return spec


def expect_something_unbound(spec: dict) -> dict:
    spec['expect']['co2'] = {'units': 't'}
    return spec


def covers_a_foreign_dim(spec: dict) -> dict:
    spec['expect']['p_max'] = {'covers': 'snapshot'}
    return spec


def units_the_source_never_declared(spec: dict) -> dict:
    spec['sources']['gen']['units'] = {}
    spec['expect']['p_max'] = {'units': 'MW'}
    return spec


def a_unit_that_does_not_match(spec: dict) -> dict:
    spec['expect']['p_max'] = {'units': 'kW'}
    return spec


@pytest.mark.parametrize(
    ('mutate', 'message'),
    [
        pytest.param(rename_bound, "Did you mean 'p_max'?", id='parameter-the-model-never-declared'),
        pytest.param(drop_a_binding, 'parameters no binding supplies: load', id='parameter-nothing-binds'),
        pytest.param(wrong_dims, 'dim sets must be equal', id='bound-over-the-wrong-dims'),
        pytest.param(unknown_source, "Did you mean 'gen'?", id='source-that-is-not-declared'),
        pytest.param(unknown_dimension, 'does not declare as a dimension', id='coords-for-a-dim-that-is-not-one'),
        pytest.param(coords_for_a_model_declared_dim, 'Drop one of the two', id='members-declared-in-both-places'),
        pytest.param(no_members_anywhere, 'shift reads positionally', id='dim-with-no-declared-members'),
        pytest.param(expect_something_unbound, 'which is not bound', id='expectation-on-nothing'),
        pytest.param(covers_a_foreign_dim, 'not one of its dims', id='covers-a-dim-the-parameter-lacks'),
        pytest.param(units_the_source_never_declared, 'declares no unit', id='unit-expected-but-never-declared'),
        pytest.param(a_unit_that_does_not_match, "declares 'MW' for column 'cap'", id='unit-mismatch'),
    ],
)
def test_what_is_refused_before_a_source_is_opened(bindings, mutate, message):
    with pytest.raises(BindingError, match=re.escape(message)):
        check(mutate(copy.deepcopy(bindings)), MODEL)


def test_the_unmutated_pair_passes(bindings):
    assert check(bindings, MODEL) is None, 'the control for every case above — it must not raise'

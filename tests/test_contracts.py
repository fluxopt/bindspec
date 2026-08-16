from __future__ import annotations

import copy
import re
from typing import TYPE_CHECKING

import pytest

from bindspec import ContractError, SourceError, bind
from tests.conftest import MODEL

if TYPE_CHECKING:
    from pathlib import Path


def duplicate_coordinate(spec: dict, workspace: Path) -> dict:
    (workspace / 'gen.csv').write_text('name,cap\nwind,100.0\nwind,40.0\ngas,200.0\n')
    return spec


def a_null_value(spec: dict, workspace: Path) -> dict:
    (workspace / 'demand.csv').write_text('hour,mw\n0,80.0\n1,\n')
    return spec


def below_the_floor(spec: dict, workspace: Path) -> dict:
    (workspace / 'gen.csv').write_text('name,cap\nwind,-1.0\ngas,200.0\n')
    spec['expect']['p_max'] = {'range': [0, None]}
    return spec


def above_the_ceiling(spec: dict, workspace: Path) -> dict:
    spec['expect']['load'] = {'range': [None, 100]}
    return spec


def a_member_with_no_row(spec: dict, workspace: Path) -> dict:
    (workspace / 'gen.csv').write_text('name,cap\nwind,100.0\n')
    spec['expect']['p_max'] = {'covers': True}
    return spec


@pytest.mark.parametrize(
    ('mutate', 'message'),
    [
        pytest.param(duplicate_coordinate, 'sharing a coordinate with another', id='two-rows-for-one-coordinate'),
        pytest.param(a_null_value, 'null value', id='a-null-where-a-number-was-expected'),
        pytest.param(below_the_floor, 'the lowest is -1.0', id='below-the-declared-floor'),
        pytest.param(above_the_ceiling, 'the highest is 120.0', id='above-the-declared-ceiling'),
        pytest.param(a_member_with_no_row, '1 of its 2 members', id='a-coordinate-the-data-never-mentions'),
    ],
)
def test_what_is_refused_once_the_data_is_read(bindings, workspace, mutate, message):
    with pytest.raises(ContractError, match=re.escape(message)):
        bind(mutate(copy.deepcopy(bindings), workspace), MODEL)


def test_a_missing_row_is_not_a_failure_unless_covers_says_so(bindings, workspace):
    (workspace / 'gen.csv').write_text('name,cap\nwind,100.0\n')
    binding = bind(bindings, MODEL)
    assert binding.sources['p_max'].height == 1, (
        'sparse data gives sparse variables — that is lpspec, and it is deliberate'
    )


def test_a_source_that_moved_says_which_one(bindings, workspace):
    (workspace / 'gen.csv').unlink()
    with pytest.raises(SourceError, match='does not exist'):
        bind(bindings, MODEL)


def test_a_format_with_no_reader_says_what_there_is(bindings, workspace):
    (workspace / 'gen.xlsx').write_text('not really')
    bindings['sources']['gen']['path'] = str(workspace / 'gen.xlsx')
    with pytest.raises(SourceError, match=re.escape("not '.xlsx'")):
        bind(bindings, MODEL)


def test_a_pin_that_no_longer_matches_refuses_the_bind(bindings, workspace):
    bindings['sources']['gen']['sha256'] = '0' * 64
    with pytest.raises(SourceError, match='re-pin it deliberately'):
        bind(bindings, MODEL)


def test_a_pin_that_matches_binds(bindings, workspace):
    digest = bind(bindings, MODEL).manifest['sources']['gen']['sha256']
    bindings['sources']['gen']['sha256'] = digest
    assert bind(bindings, MODEL).manifest['sources']['gen']['sha256'] == digest

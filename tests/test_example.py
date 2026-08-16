from __future__ import annotations

import lpspec as lps
import pytest

import bindspec as bs
from bindspec.__main__ import main
from tests.conftest import EXAMPLE


@pytest.fixture(scope='module')
def binding() -> bs.Binding:
    return bs.bind(EXAMPLE / 'bindings.yaml', EXAMPLE / 'model.yaml')


def test_what_bindspec_hands_over_is_what_lpspec_takes(binding):
    with lps.solve(EXAMPLE / 'model.yaml', binding.sources) as result:
        assert result.is_ok
        assert result.objective == pytest.approx(1000.0), 'only the 180 MW hour needs gas: 20 MW at 50 EUR/MWh'


def test_the_coordinate_carries_its_declared_order(binding):
    assert binding.sources['snapshot']['snapshot'].to_list() == [0, 1, 2, 3, 4, 5], (
        'order of first appearance in the source column, not sorted — shift reads it positionally'
    )
    assert 'generator' not in binding.sources, 'the model declares those members, so the bindings must not supply them'


def test_the_manifest_records_what_was_read(binding):
    manifest = binding.manifest
    assert set(manifest['parameters']) == {'p_max', 'cost', 'load'}
    assert manifest['parameters']['load'] == {
        'source': 'demand',
        'column': 'mw',
        'rows': 6,
        'units': 'MW',
        'checked': ['keyed', 'units', 'non_null', 'covers:snapshot'],
    }
    assert len(manifest['sources']['demand']['sha256']) == 64, 'a pin is what makes the record reproducible'


def test_the_manifest_is_the_same_twice(binding):
    assert bs.bind(EXAMPLE / 'bindings.yaml', EXAMPLE / 'model.yaml').manifest == binding.manifest, (
        'no timestamps, no ordering by iteration: the same bytes produce the same record'
    )


def test_the_command_checks_without_reading(capsys):
    assert main(['check', str(EXAMPLE / 'bindings.yaml'), str(EXAMPLE / 'model.yaml')]) == 0
    assert 'nothing decidable without data is wrong' in capsys.readouterr().out


def test_the_command_reports_a_failure_on_stderr(capsys, tmp_path):
    (tmp_path / 'bindings.yaml').write_text('bind: {load: {from: nowhere, value: mw}}\n')
    assert main(['check', str(tmp_path / 'bindings.yaml'), str(EXAMPLE / 'model.yaml')]) == 1
    assert 'BindingError' in capsys.readouterr().err

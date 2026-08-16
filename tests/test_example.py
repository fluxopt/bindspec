from __future__ import annotations

import re

import lpspec as lps
import pytest

import bindspec as bs
from bindspec.__main__ import main
from tests.conftest import EXAMPLE, assert_golden, run_example


@pytest.fixture(scope='module')
def binding() -> bs.Binding:
    return bs.bind(EXAMPLE / 'bindings.yaml', EXAMPLE / 'model.yaml')


@pytest.fixture(scope='module')
def narration() -> str:
    """One run of the whole example, shared by both tests that read it."""
    return run_example(EXAMPLE / 'run.py', 'dispatch_run')


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
    assert manifest['sources']['demand']['path'] == 'data/demand.csv', (
        'the path is recorded as declared, never as resolved: an absolute path off one laptop '
        're-derives nothing on anyone else, which is the whole job of the record'
    )


def test_the_manifest_is_the_same_twice(binding):
    assert bs.bind(EXAMPLE / 'bindings.yaml', EXAMPLE / 'model.yaml').manifest == binding.manifest, (
        'no timestamps, no ordering by iteration: the same bytes produce the same record'
    )


def test_the_narration_matches_what_is_committed(narration, pytestconfig):
    assert_golden(
        narration,
        EXAMPLE / 'run.out',
        pytestconfig,
        drifted='examples/dispatch/run.out no longer matches what the example prints, so the README\n'
        'and the docs are describing an older package. If this run is the correct story:\n'
        '    uv run pytest tests/test_example.py --update-golden\n',
    )


def test_the_narration_claims_hold(narration):
    """The golden file catches *any* change; this names the ones that matter."""
    for stage in range(1, 6):
        assert f'[{stage}]' in narration, f'stage {stage} did not run'
    assert 'objective    1000.0' in narration, 'the example still reaches the optimum it narrates'
    assert narration.count('BindingError') == 2, 'two of the three refusals happen before a source is opened'
    assert 'ContractError' in narration, 'and the coverage one needs the data, which is the point of the split'


def test_the_readme_quotes_the_example_verbatim(narration):
    quoted = re.findall(r'```text\n(.*?)```', (EXAMPLE.parents[1] / 'README.md').read_text(), re.DOTALL)
    assert quoted, 'the README should show what comes back, not only describe it'
    for block in quoted:
        assert block in narration, f'the README quotes output the example does not print:\n{block}'


def test_the_command_checks_without_reading(capsys):
    assert main(['check', str(EXAMPLE / 'bindings.yaml'), str(EXAMPLE / 'model.yaml')]) == 0
    assert 'nothing decidable without data is wrong' in capsys.readouterr().out


def test_the_command_reports_a_failure_on_stderr(capsys, tmp_path):
    (tmp_path / 'bindings.yaml').write_text('bind: {load: {from: nowhere, value: mw}}\n')
    assert main(['check', str(tmp_path / 'bindings.yaml'), str(EXAMPLE / 'model.yaml')]) == 1
    assert 'BindingError' in capsys.readouterr().err

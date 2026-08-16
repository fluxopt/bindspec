from __future__ import annotations

import contextlib
import difflib
import importlib.util
import io
import sys
from pathlib import Path

import pytest

EXAMPLE = Path(__file__).resolve().parents[1] / 'examples' / 'dispatch'


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        '--update-golden',
        action='store_true',
        default=False,
        help='rewrite committed golden output (examples/**/*.out) from this run instead of asserting on it',
    )


def run_example(path: Path, name: str) -> str:
    """Import a script as module ``name`` and capture what its ``main()`` prints."""
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            module.main()
    finally:
        del sys.modules[name]
    return buffer.getvalue()


def assert_golden(output: str, golden: Path, pytestconfig: pytest.Config, drifted: str) -> None:
    """``output`` matches the committed golden, or ``--update-golden`` rewrites it.

    Args:
        output: What this run printed.
        golden: The committed file to compare against or rewrite.
        pytestconfig: The fixture, for the ``--update-golden`` flag.
        drifted: What a mismatch means for this example — opens the failure
            message, above the diff, and should say how to regenerate.
    """
    if pytestconfig.getoption('--update-golden'):
        golden.write_text(output)
        pytest.skip(f'rewrote {golden.name} from this run')
    expected = golden.read_text()
    if output != expected:
        diff = '\n'.join(difflib.unified_diff(expected.splitlines(), output.splitlines(), 'committed', 'this run'))
        pytest.fail(f'{drifted}\n{diff}', pytrace=False)


#: Two dims exercising both ways a coordinate arrives: declared in the model,
#: and supplied by the bindings.
MODEL = {
    'dimensions': {'snapshot': {'dtype': 'int'}, 'generator': {'values': ['wind', 'gas']}},
    'parameters': {'p_max': {'dims': ['generator']}, 'load': {'dims': ['snapshot']}},
}


@pytest.fixture
def workspace(tmp_path: Path) -> Path:
    (tmp_path / 'gen.csv').write_text('name,cap\nwind,100.0\ngas,200.0\n')
    (tmp_path / 'demand.csv').write_text('hour,mw\n0,80.0\n1,120.0\n')
    return tmp_path


@pytest.fixture
def bindings(workspace: Path) -> dict:
    return {
        'sources': {
            'gen': {'path': str(workspace / 'gen.csv'), 'units': {'cap': 'MW'}},
            'demand': {'path': str(workspace / 'demand.csv'), 'units': {'mw': 'MW'}},
        },
        'coords': {'snapshot': {'from': 'demand', 'column': 'hour'}},
        'bind': {
            'p_max': {'from': 'gen', 'dims': {'generator': 'name'}, 'value': 'cap'},
            'load': {'from': 'demand', 'dims': {'snapshot': 'hour'}, 'value': 'mw'},
        },
        'expect': {},
    }

from __future__ import annotations

from pathlib import Path

import pytest

EXAMPLE = Path(__file__).resolve().parents[1] / 'examples' / 'dispatch'

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

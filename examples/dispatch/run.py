"""What bindspec does, one call at a time — run it and read.

    uv run python examples/dispatch/run.py

Its output is committed as ``run.out`` and asserted line for line by
``tests/test_example.py``, so a message that changes fails CI rather than
leaving a README that quietly describes an older package. Regenerate it with
``uv run pytest tests/test_example.py --update-golden``.

The point it makes is the README's claim: the model says what the math is, and
these files say which bytes filled it, what had to be true of them, and what
comes back so that somebody else can re-derive the answer.
"""

from __future__ import annotations

import contextlib
import copy
import json
from pathlib import Path
from typing import Any

import lpspec as lps
import yaml

import bindspec as bs

HERE = Path(__file__).parent


def refused(bindings: dict[str, Any]) -> str:
    """Bind a deliberately broken copy of the bindings and return what it earns."""
    try:
        bs.bind(bindings, 'model.yaml')
    except bs.BindspecError as error:
        return f'{type(error).__name__}: {error}'
    raise AssertionError('that mutation was supposed to be refused')


def main() -> None:
    with contextlib.chdir(HERE):
        print('bindings.yaml says which bytes fill model.yaml, and what must be true of them.')

        print('\n[1] check -- nothing is opened')
        bs.check('bindings.yaml', 'model.yaml')
        print('    every parameter bound once, every dim set equal, every dimension')
        print('    carrying declared members, every expected unit matching its source: ok')

        print('\n[2] bind -- read, then check what was read')
        binding = bs.bind('bindings.yaml', 'model.yaml')
        for name, record in binding.manifest['parameters'].items():
            print(f'    {name:<9}{record["rows"]:>3} rows  {record["units"]:<9} {", ".join(record["checked"])}')
        for dim, record in binding.manifest['coords'].items():
            print(f'    {dim:<9}{record["members"]:>3} members, from the {record["from"]}')

        print('\n[3] solve -- the mapping goes straight to lpspec, unchanged')
        print(f'    handed over  {", ".join(sorted(binding.sources))}')
        with lps.solve('model.yaml', binding.sources) as result:
            print(f'    status       {result.status}')
            print(f'    objective    {result.objective}')

        print('\n[4] the manifest -- what a reader needs to re-derive that number')
        for line in json.dumps(binding.manifest, indent=2, sort_keys=True).splitlines():
            print(f'    {line}')

        print('\n[5] what is refused, and what the message says to do')
        good = yaml.safe_load(Path('bindings.yaml').read_text())

        stated_in_the_wrong_unit = copy.deepcopy(good)
        stated_in_the_wrong_unit['expect']['p_max']['units'] = 'kW'
        print(f'\n    a unit nobody converted:\n      {refused(stated_in_the_wrong_unit)}')

        members_left_to_be_derived = copy.deepcopy(good)
        del members_left_to_be_derived['coords']['snapshot']
        print(f'\n    a dimension whose members nobody declared:\n      {refused(members_left_to_be_derived)}')

        an_older_export = copy.deepcopy(good)
        an_older_export['sources']['generators']['path'] = 'data/generators_missing_gas.csv'
        print(f'\n    a coordinate the data never mentions:\n      {refused(an_older_export)}')

        print('\n    The third one is the whole argument for this package: lpspec would')
        print('    have built that model, solved it, and returned a cheaper answer.')


if __name__ == '__main__':
    main()

"""``python -m bindspec`` — check a pair, or write the manifest for one."""

from __future__ import annotations

import argparse
import json
import sys

from bindspec.binding import bind, check
from bindspec.errors import BindspecError


def main(argv: list[str] | None = None) -> int:
    """Run the CLI, returning the process exit status."""
    parser = argparse.ArgumentParser(prog='bindspec', description='Bind a model to its data, and say what was read.')
    commands = parser.add_subparsers(dest='command', required=True)
    for name, help_text in (
        ('check', 'refuse a pair that cannot work, reading nothing'),
        ('manifest', 'read, check, and record'),
    ):
        sub = commands.add_parser(name, help=help_text)
        sub.add_argument('bindings')
        sub.add_argument('model')
        if name == 'manifest':
            sub.add_argument('-o', '--output', help='write here instead of stdout')

    args = parser.parse_args(argv)
    try:
        if args.command == 'check':
            check(args.bindings, args.model)
            print(f'{args.bindings} binds {args.model}: nothing decidable without data is wrong.')
            return 0
        binding = bind(args.bindings, args.model)
    except BindspecError as error:
        print(f'{type(error).__name__}: {error}', file=sys.stderr)
        return 1
    if args.output:
        print(f'wrote {binding.write_manifest(args.output)}')
    else:
        print(json.dumps(binding.manifest, indent=2, sort_keys=True, default=str))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

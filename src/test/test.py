

import argparse

class OptionalDestination:
    def __init__(self):
        self.value = "<not-set>"

    def __call__(self, s):
        if s.startswith('@'):
            self.value = s

        raise argparse.ArgumentTypeError('not it')
        # raise TypeError('not it')

    def __repr__(self):
        return self.value

parser = argparse.ArgumentParser()
parser.add_argument('-t', '--timeout', type=int, default=10)
parser.add_argument('-v', '--verbose', action='store_true', default=False)
# parser.add_argument('destination', nargs="?", type=OptionalDestination(), )
parser.add_argument('destination', nargs=argparse.OPTIONAL, type=str)
parser.add_argument('command', type=str)
parser.add_argument('all_other', nargs=argparse.REMAINDER)


args = parser.parse_args(['-t 12', '-v', '@rover', 'list'])

print(f"Got -t {args.timeout} -v {args.verbose} @ {args.destination} execute {args.command}; other: {args.all_other}")

args = parser.parse_args(['list', '1', '2', '-b', '-t', '99'])

print(f"Got -t {args.timeout} -v {args.verbose} @ {args.destination} execute {args.command}; other: {args.all_other}")

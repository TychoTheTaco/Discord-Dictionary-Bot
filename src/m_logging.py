import sys


def log(message, level='info'):
    if level in ['e', 'error']:
        print(f'[ERROR] {message}', file=sys.stderr)
    else:
        print(f'[INFO ] {message}')
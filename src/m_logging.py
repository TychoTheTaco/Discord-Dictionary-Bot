import sys
import time


def log(message, level='info'):
    # Add timestamp
    timestamp = time.strftime("%m/%d/%Y %H:%M:%S")
    result = f'[{timestamp}]'

    # Add log level
    file = sys.stdout
    if level in ['e', 'error']:
        result += ' [ERROR]'
        file = sys.stderr
    else:
        result += ' [INFO ]'

    # Add message
    result += f' {message}'

    # Write message
    print(f'{result}', file=file)

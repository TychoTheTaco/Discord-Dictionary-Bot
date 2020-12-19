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
    elif level in ['i', 'info']:
        result += ' [INFO ]'
    elif level in ['w', 'warn']:
        result += ' [WARN ]'

    # Add message
    result += f' {message}'

    # Write message
    print(f'{result}', file=file)

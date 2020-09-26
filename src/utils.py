import discord


def get_token(path='token.txt'):
    with open(path) as file:
        return file.read()


async def send_split(message: str, channel: discord.TextChannel, split_size=2000):
    """
    Send a message to the specified tet channel. If the message is longer than Discord's limit of 2000 characters, the message will be split up and sent separately.
    :param message:
    :param channel:
    :param split_size:
    :return:
    """
    messages = split_formatting(message, split_size)
    for m in messages:
        await channel.send(m)


def find_active_formatting(message):
    """
    Italics: * or _
    Bold: **
    Underline: __
    :param message:
    :return:
    """
    active = []
    p = ''
    a = 0
    for i, c in enumerate(message):

        # Detect bold/italics
        if c == '*':
            if p == '*':
                if 'bold' not in active:
                    active.append('bold')
                else:
                    active.remove('bold')
                a = i
        elif p == '*':
            if 'italics' not in active and i - 1 != a:
                active.append('italics')
                #print('italics START', i - 1)
                a = i - 1
            elif 'italics' in active:
                active.remove('italics')
                #print('italics END', i - 1)

        # Detect underline/italics
        if c == '_':
            if p == '_':
                if 'underline' not in active:
                    active.append('underline')
                else:
                    active.remove('underline')
                a = i
        elif p == '_':
            if 'italics' not in active and i - 1 != a:
                active.append('italics')
                #print('italics START', i - 1)
                a = i - 1
            elif 'italics' in active:
                active.remove('italics')
                #print('italics END', i - 1)

        p = c
    return active


def split_formatting(message: str, split_size=30):
    """
    Split the given message while attempting to keep markdown formatting intact.
    :param message: The message to split.
    :param split_size: The maximum length (in characters) of any message segment.
    :return: A list of message segments.
    """
    messages = []
    while len(message) > 0:

        # Take first 'split_size' characters
        m = message[:split_size]
        message = message[split_size:]

        # Check formatting
        active = find_active_formatting(m)

        # close formatting in reverse order
        code = ''
        for x in reversed(active):
            if x == 'bold':
                code += '**'
            elif x == 'italics':
                code += '*'
            elif x == 'underline':
                code += '__'

        if len(code) > 0:
            if len(m) + len(code) <= split_size:
                m += code
            else:
                a = m[:-len(code)]
                b = m[-len(code):]
                m = a + code
                message = code[::-1] + b + message
        messages.append(m)

    return messages

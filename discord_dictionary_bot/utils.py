import re
import logging

import discord

# Set up logging
logger = logging.getLogger(__name__)


def get_token(path='token.txt'):
    with open(path) as file:
        return file.read()


async def send_or_dm(message: str, channel: discord.abc.Messageable, user: discord.User):
    """
    Send a message to the specified channel. If we don't have permission to send messages in that channel, this will send the message as a DM to the user instead.
    :param message:
    :param channel:
    :param user:
    :return:
    """
    if len(message) > 2000:
        message = message[:2000]
        logger.error('Message length too long!')
    try:
        await channel.send(message)
    except discord.errors.Forbidden:
        logger.warning(f'Failed to send message to channel {channel}. Sending it as a DM to user {user} instead.')
        await user.send(f'**I do not have permission to send messages in `{channel}` so I am responding to you here:**')
        await user.send(message)


async def send_split(message: str, channel: discord.abc.Messageable, split_size=2000, delim=None):
    """
    Send a message to the specified tet channel. If the message is longer than Discord's limit of 2000 characters, the message will be split up and sent separately.
    :param message:
    :param channel:
    :param split_size:
    :param delim:
    :return:
    """
    messages = split_formatting(message, split_size, delim=delim)
    for m in messages:
        await channel.send(m)


async def send_split_nf(message: str, channel: discord.abc.Messageable, split_size=2000, delim=None):
    """
    Send a message to the specified tet channel. If the message is longer than Discord's limit of 2000 characters, the message will be split up and sent separately.
    :param message:
    :param channel:
    :param split_size:
    :param delim:
    :return:
    """
    messages = split(message, split_size, delim=delim)
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

        # Detect code block
        if c == '`':
            if 'code' not in active:
                active.append('code')
            else:
                active.remove('code')
            a = i

        if 'code' not in active:
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
                    # print('italics START', i - 1)
                    a = i - 1
                elif 'italics' in active:
                    active.remove('italics')
                    # print('italics END', i - 1)

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
                    # print('italics START', i - 1)
                    a = i - 1
                elif 'italics' in active:
                    active.remove('italics')
                    # print('italics END', i - 1)

        p = c
    return active


def split(message: str, split_size: int, delim='\n'):
    # print('MESSAGE LENGTH:', len(message))
    blocks = []

    # Find valid split locations
    pattern = re.compile(delim)
    matches = [m.span() for m in pattern.finditer(message)]
    # print('MATCHES:', matches)

    i = 0
    while i < len(message) - 1:
        end_index = min(i + split_size - 1, len(message) - 1)
        # print('SUB STR', i, end_index)
        block_size = end_index - i

        # Find the nearest valid split index
        if end_index < len(message) - 1:
            s = (end_index, end_index)
            while len(matches) > 0:
                s = matches[0]
                matches = matches[1:]
                if len(matches) > 0:
                    if matches[0][0] > end_index:
                        break

            # print('SPLIT AT', s)
            block_size = s[0] + 1 - i

        blocks.append(message[i:i + block_size])

        # print('BLOCK SIZE', block_size)
        i += block_size

    return blocks


def split_formatting(message: str, split_size=30, delim=None):
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

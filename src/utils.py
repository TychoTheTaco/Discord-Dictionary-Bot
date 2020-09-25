import discord


def get_token(path='token.txt'):
    with open(path) as file:
        return file.read()


async def send(message: str, channel: discord.TextChannel, split_size=2000):
    """
    Send a message to the specified tet channel. If the message is longer than Discord's limit of 2000 characters, the message will be split up and sent separately.
    :param message:
    :param channel:
    :param split_size:
    :return:
    """
    messages = [message[i:i + split_size] for i in range(0, len(message), split_size)]
    for m in messages:
        await channel.send(m)

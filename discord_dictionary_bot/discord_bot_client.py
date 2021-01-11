import asyncio
import threading
import discord
import utils
from exceptions import InsufficientPermissionsException
from properties import Properties
import logging

# Set up logging
logger = logging.getLogger(__name__)


class DiscordBotClient(discord.Client):
    """
    A general discord bot client that supports 'Command's and includes some other helper functions.
    """

    def __init__(self):
        super().__init__()

        # Initialize properties
        self._properties = Properties()

        # List of commands this bot supports. All bots support the 'Help' and 'Property' commands by default. Subclasses can add more by calling 'add_command()'.
        from commands import HelpCommand, PropertyCommand
        self._commands = [HelpCommand(self), PropertyCommand(self, self._properties)]

    @property
    def commands(self):
        return self._commands

    @property
    def properties(self):
        return self._properties

    def add_command(self, command: 'commands.Command') -> None:
        """
        Add a command to this discord bot client.
        :param command: The command to add.
        """
        self._commands.append(command)

    def get_prefix(self, channel: discord.TextChannel) -> str:
        """
        Get this bot's summon prefix for the specified text channel. It will usually be the same for all channels in a server but may vary between servers.
        :param channel: The text channel.
        :return: The summon prefix.
        """
        return self._properties.get(channel, 'prefix')

    async def join_voice_channel(self, voice_channel: discord.VoiceChannel) -> discord.VoiceProtocol:
        """
        Connect to the specified voice channel if we are not already connected.
        :param voice_channel: The voice channel to connect to.
        :return: A 'discord.VoiceClient' representing our voice connection.
        """

        # Make sure we have permission to join the voice channel. If we try to join a voice channel without permission, it will timeout.
        permissions = voice_channel.permissions_for(voice_channel.guild.me)
        if not all([permissions.view_channel, permissions.connect, permissions.speak]):
            raise InsufficientPermissionsException(['View Channel', 'Connect', 'Speak'])

        # Check if we are already connected to this voice channel
        for voice_client in self.voice_clients:
            if voice_client.channel == voice_channel:
                return voice_client

        # Connect to the voice channel
        return await voice_channel.connect()

    async def leave_voice_channel(self, voice_channel: discord.VoiceChannel) -> None:
        """
        Leave the specified voice channel if we were connected to it.
        :param voice_channel: The voice channel to leave.
        """
        for voice_client in self.voice_clients:
            if voice_client.channel == voice_channel:
                await voice_client.disconnect()

    def sync(self, coroutine):
        """
        Submit a coroutine to the client's event loop.
        :param coroutine: A coroutine to run on this client's event loop.
        """
        return asyncio.run_coroutine_threadsafe(coroutine, self.loop)

    async def on_ready(self):
        print(f'Logged on as {self.user}!')

    async def on_message(self, message: discord.Message):

        # Ignore our own messages
        if message.author == self.user:
            return

        # Check what prefix we have in this channel
        prefix = self.get_prefix(message.channel)
        if type(prefix) is not str:
            logger.critical(f'Message: "{message.content}"')
            logger.critical(f'Invalid prefix: "{prefix}" M: "{message}" G: "{message.guild}" C: "{message.channel}"')

        # Check if the message starts with our prefix
        if not message.content.startswith(prefix):
            return

        # Ignore messages with mentions
        if len(message.mentions) + len(message.channel_mentions) + len(message.role_mentions) > 0:
            await utils.send_split('I don\'t approve of ping spamming.', message.channel)
            return

        # Parse input
        command_input = message.content[len(prefix):].lower().split(' ')

        # Execute command
        for command in self._commands:
            if command.matches(command_input[0]):
                threading.Thread(target=command.execute, args=[message, command_input[1:]]).start()  # This doesn't seem like a good idea but it prevents blocking
                return

        # Send invalid command message
        from commands import HelpCommand
        await utils.send_split(f'Unrecognized command. Use `{prefix + HelpCommand(self).name}` to see available commands.', message.channel)

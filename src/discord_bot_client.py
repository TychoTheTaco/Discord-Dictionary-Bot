import asyncio
import threading
import discord
from commands.command import Command
from commands.help import HelpCommand
import utils


class DiscordBotClient(discord.Client):
    """
    A general discord bot client that supports 'Command's and includes some other helper functions.
    """

    def __init__(self):
        super().__init__()
        self._commands = [HelpCommand(self)]

    @property
    def commands(self):
        return self._commands

    def add_command(self, command: Command) -> None:
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
        return '!'

    async def join_voice_channel(self, voice_channel: discord.VoiceChannel) -> discord.VoiceClient:
        """
        Connect to the specified voice channel if we are not already connected.
        :param voice_channel: The voice channel to connect to.
        :return: A 'discord.VoiceClient' representing our voice connection.
        """
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

    async def on_message(self, message: discord.Message):

        # Ignore our own messages
        if message.author == self.user:
            return

        # Check what prefix we have in this channel or server
        prefix = self.get_prefix(message.channel)

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
                threading.Thread(target=command.execute, args=[message, command_input[1:]]).start()
                return

        # Send invalid command message
        await utils.send_split(f'Unrecognized command. Use `{prefix + HelpCommand(self).name}` to see available commands.', message.channel)

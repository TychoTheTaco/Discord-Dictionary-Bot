import discord
import pathlib
import asyncio
import utils

from commands.help import HelpCommand
from commands.define import DefineCommand
from commands.stop import StopCommand
from commands.define_backwards import DefineReverseCommand
from commands.next import NextCommand
from commands.lang_list import LangListCommand
from commands.property import PropertyCommand

from definition_response_manager import DefinitionResponseManager
from properties import Properties


class DictionaryBotClient(discord.Client):

    def __init__(self, ffmpeg_path: str):
        """
        A simple dictionary bot.
        :param ffmpeg_path: Path to the ffmpeg executable.
        """
        super().__init__()

        # Load properties
        self._properties = Properties()

        # Load commands
        self._definition_response_manager = DefinitionResponseManager(self, pathlib.Path(ffmpeg_path))
        self._commands = [
            HelpCommand(self),
            DefineCommand(self, self._definition_response_manager),
            DefineReverseCommand(self, self._definition_response_manager),
            StopCommand(self, self._definition_response_manager),
            NextCommand(self, self._definition_response_manager),
            LangListCommand(self),
            PropertyCommand(self, self._properties)
        ]

    @property
    def commands(self):
        return self._commands

    @property
    def properties(self):
        return self._properties

    async def on_ready(self):
        print(f'Logged on as {self.user}!')

    async def on_message(self, message: discord.Message):

        # Check what prefix we have on this server
        prefix = self._properties.get(message.guild, 'prefix')

        # Ignore our own messages
        if message.author == self.user:
            return

        # Check for prefix
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
                command.execute(message, command_input[1:])
                return

        # Send invalid command message
        await utils.send_split(f'Unrecognized command. Use `{prefix + HelpCommand(self).name}` to see available commands.', message.channel)

    def get_voice_client(self, voice_channel: discord.VoiceChannel):
        for voice_client in self.voice_clients:
            if voice_client.channel == voice_channel:
                return voice_client
        return None

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
        for voice_client in self.voice_clients:
            if voice_client.channel == voice_channel:
                await voice_client.disconnect()

    def sync(self, coroutine):
        """
        Submit a coroutine to the client's event loop.
        :param coroutine:
        """
        return asyncio.run_coroutine_threadsafe(coroutine, self.loop)
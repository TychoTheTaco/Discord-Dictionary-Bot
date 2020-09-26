import discord
import pathlib
import argparse
import asyncio

import utils

from commands.help import HelpCommand
from commands.define import DefineCommand
from commands.stop import StopCommand
from commands.define_backwards import DefineReverseCommand
from commands.next import NextCommand

from definition_response_manager import DefinitionResponseManager

TOKEN_FILE_PATH = pathlib.Path('../token.txt')
FFMPEG_EXE_PATH = None  # Set by argparse

PREFIX = '.'


class DictionaryBotClient(discord.Client):

    def __init__(self):
        super().__init__()
        self._definition_response_manager = DefinitionResponseManager(self, FFMPEG_EXE_PATH)
        self._commands = [
            HelpCommand(self),
            DefineCommand(self, self._definition_response_manager),
            DefineReverseCommand(self, self._definition_response_manager),
            StopCommand(self, self._definition_response_manager),
            NextCommand(self, self._definition_response_manager)
        ]

    @property
    def commands(self):
        return self._commands

    async def on_ready(self):
        print(f'Logged on as {self.user}!')

    async def on_message(self, message: discord.Message):

        # Ignore our own messages
        if message.author == self.user:
            return

        # Check for prefix
        if not message.content.startswith(PREFIX):
            return

        # Parse input
        command_input = message.content[1:].lower().split(' ')

        # Execute command
        for command in self._commands:
            if command.matches(command_input[0]):
                command.execute(message, command_input[1:])
                return

        # Send invalid command message
        await utils.send_split(f'Unrecognized command. Use `{PREFIX + HelpCommand(self).name}` to see available commands.', message.channel)

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


if __name__ == '__main__':

    # Parse arguments
    parser = argparse.ArgumentParser()
    parser.add_argument('-t', help='Token to use when running the bot.', dest='token', default=None)
    parser.add_argument('-f', help='Path to ffmpeg executable', dest='ffmpeg_exe_path', default='ffmpeg')
    args = parser.parse_args()

    FFMPEG_EXE_PATH = args.ffmpeg_exe_path
    token = args.token if args.token is not None else utils.get_token(path='../token.txt')

    # Start client
    client = DictionaryBotClient()
    client.run(token)

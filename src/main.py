import discord
import pathlib
import argparse

from commands.help import HelpCommand
from commands.define import DefineCommand
from commands.stop import StopCommand
from commands.define_backwards import DefineReverseCommand

from definition_response_manager import DefinitionResponseManager

PROJECT_ROOT = pathlib.Path('../')
TOKEN_FILE_PATH = pathlib.Path(PROJECT_ROOT, 'token.txt')
FFMPEG_EXE_PATH = None  # Set by argparse

PREFIX = '.'


def get_token(path='token.txt'):
    with open(path) as file:
        return file.read()


class DictionaryBotClient(discord.Client):

    def __init__(self, *, loop=None, **options):
        super().__init__(loop=loop, **options)
        self._definition_response_manager = DefinitionResponseManager(self, FFMPEG_EXE_PATH)
        self._commands = [
            HelpCommand(self),
            DefineCommand(self, self._definition_response_manager),
            DefineReverseCommand(self, self._definition_response_manager),
            StopCommand(self, self._definition_response_manager)
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

        # Parse command
        command_input = message.content[1:].lower().split(' ')

        for command in self._commands:
            if command.matches(command_input[0]):
                command.execute(message, command_input[1:])
                # elif command._name == 'define':
                #     # Extract word from command
                #     word = ' '.join(command_input[1:])
                #
                #     # Add word to the queue
                #     text_to_speech = len(command_input[0]) == 2 and command_input[0][1] == 'v'
                #     self._definition_response_manager.add(word, message, command_input[0][0] == 'b', text_to_speech=text_to_speech)
                # elif command._name == 'stop':
                #     # Clear word queue
                #     await self._definition_response_manager.clear(message.channel)
                break

        print('Ready.')

    async def join_voice_channel(self, voice_channel: discord.VoiceChannel) -> discord.VoiceClient:
        """
        Connect to the specified voice channel if we are not already connected.
        :param voice_channel: The voice channel to connect to.
        :return: A 'discord.VoiceClient' representing our voice connection.
        """
        # Check if we are already connected to this voice channel
        for voice_client in self.voice_clients:
            print(voice_client)
            if voice_client.channel == voice_channel:
                return voice_client

        # Connect to the voice channel
        return await voice_channel.connect()

    async def leave_voice_channel(self, voice_channel: discord.VoiceChannel) -> None:
        for voice_client in self.voice_clients:
            if voice_client.channel == voice_channel:
                await voice_client.disconnect()


if __name__ == '__main__':

    # Parse arguments
    parser = argparse.ArgumentParser()
    parser.add_argument('-t', help='Token to use when running the bot.', dest='token', default=None)
    parser.add_argument('-f', help='Path to ffmpeg executable', dest='ffmpeg_exe_path', default='ffmpeg')
    args = parser.parse_args()

    FFMPEG_EXE_PATH = args.ffmpeg_exe_path

    # Create client
    client = DictionaryBotClient()

    # Start client
    if args.token is None:
        client.run(get_token(path='../token.txt'))
    else:
        client.run(args.token)

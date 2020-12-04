import discord
import pathlib
import asyncio
import utils

from discord_bot_client import DiscordBotClient

from commands.help import HelpCommand
from commands.define_forwards import DefineForwardsCommand
from commands.stop import StopCommand
from commands.define_backwards import DefineReverseCommand
from commands.next import NextCommand
from commands.lang_list import LangListCommand
from commands.property import PropertyCommand

from definition_response_manager import DefinitionResponseManager
from properties import Properties


class DictionaryBotClient(DiscordBotClient):

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
        self.add_command(DefineForwardsCommand(self, self._definition_response_manager))
        self.add_command(DefineReverseCommand(self, self._definition_response_manager))
        self.add_command(StopCommand(self, self._definition_response_manager))
        self.add_command(NextCommand(self, self._definition_response_manager))
        self.add_command(LangListCommand(self))
        self.add_command(PropertyCommand(self, self._properties))

    @property
    def properties(self):
        return self._properties

    def get_prefix(self, channel: discord.TextChannel) -> str:
        return self._properties.get(channel, 'prefix')

    async def on_ready(self):
        print(f'Logged on as {self.user}!')

    def sync(self, coroutine):
        """
        Submit a coroutine to the client's event loop.
        :param coroutine:
        """
        return asyncio.run_coroutine_threadsafe(coroutine, self.loop)
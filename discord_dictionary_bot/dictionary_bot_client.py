import pathlib
from .discord_bot_client import DiscordBotClient

from .commands import *
from .definition_response_manager import DefinitionResponseManager
from .dictionary_api import DictionaryAPI


class DictionaryBotClient(DiscordBotClient):

    def __init__(self, ffmpeg_path: str, dictionary_api: DictionaryAPI):
        """
        A simple discord dictionary bot.
        :param ffmpeg_path: Path to the ffmpeg executable. Used for converting text-to-speech to the correct audio format.
        :param dictionary_api: The dictionary API to use for getting definitions.
        """
        super().__init__()

        # Load commands
        self._definition_response_manager = DefinitionResponseManager(self, pathlib.Path(ffmpeg_path), dictionary_api)
        self.add_command(DefineForwardsCommand(self, self._definition_response_manager))
        self.add_command(DefineReverseCommand(self, self._definition_response_manager))
        self.add_command(StopCommand(self, self._definition_response_manager))
        self.add_command(NextCommand(self, self._definition_response_manager))
        self.add_command(LangListCommand(self))
        self.add_command(ActiveServerCountCommand(self))

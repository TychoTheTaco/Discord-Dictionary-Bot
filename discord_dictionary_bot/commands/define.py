import io
from contextlib import redirect_stderr
import argparse
import re

import discord
from google.cloud import texttospeech
from discord_slash import SlashContext

from ..definition_response_manager import DefinitionRequest
from .command import Command, Context
from .. import utils
from ..discord_bot_client import DiscordBotClient


class DefineCommand(Command):

    # This set stores valid language names that can be used for text-to-speech. It is filled when the first instance of 'DefineCommand' is created. All instances of 'DefineCommand' should share this set.
    _LANGUAGES = frozenset()

    def __init__(self, client: DiscordBotClient, definition_response_manager, name, aliases=None, description='', **kwargs):
        super().__init__(client, name, aliases, description, usage='[-v] [-lang <language_code>] <word>', **kwargs)
        self._definition_response_manager = definition_response_manager

        # Get a list of supported languages
        if len(DefineCommand._LANGUAGES) == 0:
            tts_client = texttospeech.TextToSpeechClient()
            response = tts_client.list_voices()
            DefineCommand._LANGUAGES = frozenset(voice.name for voice in response.voices)

    def execute(self, context: Context, args: tuple):
        try:
            parser = argparse.ArgumentParser()
            parser.add_argument('word', nargs='+')
            parser.add_argument('-v', action='store_true', default=False, dest='text_to_speech')
            parser.add_argument('-lang', '-l', dest='language', default=self.client.properties.get(context.channel, 'language'))

            # Parse arguments but suppress stderr output
            stderr_stream = io.StringIO()
            with redirect_stderr(stderr_stream):
                args = parser.parse_args(args)

        except SystemExit:
            self.client.sync(utils.send_split(f'Invalid arguments!\nUsage: `{self.name} {self.usage}`', context.channel))
            return

        # Extract word from arguments
        word = ' '.join(args.word).strip()

        self._add_request(context.author, word, context.channel, False, args.text_to_speech, args.language)
        self.client.sync(context.channel.send(f':white_check_mark: Word added to queue.'))

    def execute_slash_command(self, slash_context: SlashContext, args: tuple):
        word = args[0]
        text_to_speech = False if len(args) < 2 else args[1]
        language = self.client.properties.get(slash_context.channel, 'language') if len(args) < 3 else args[2]

        self._add_request(slash_context.author, word, slash_context.channel, False, text_to_speech, language)
        self.client.sync(slash_context.send(content=f'Added **{word}** to queue.', send_type=3))

    def _add_request(self, user: discord.User, word, channel: discord.abc.Messageable, reverse, text_to_speech, language):

        # Check for non-word characters
        pattern = re.compile('(?:[^ \\w]|\\d)')
        if pattern.search(word) is not None:
            self.client.sync(utils.send_split(f'That\'s not a word.', channel))
            return

        # TODO: Find closest matching language, prefer wavenet by default?
        if language != self.client.properties.get(channel, 'language'):
            if language not in DefineCommand._LANGUAGES:
                for language_code in DefineCommand._LANGUAGES:
                    if language.lower() in language_code.lower():
                        language = language_code
                        self.client.sync(utils.send_split(f'Incomplete language code. Assuming you mean `{language}`', channel))
                        break

        # Check for text-to-speech override
        text_to_speech_property = self.client.properties.get(channel, 'text_to_speech')
        if text_to_speech_property == 'force' and isinstance(user, discord.Member):
            text_to_speech = user.voice is not None
        elif text_to_speech_property == 'disable':
            text_to_speech = False

        # Add to definition queue
        self._definition_response_manager.add(DefinitionRequest(user, word, channel, reverse=reverse, text_to_speech=text_to_speech, language=language))

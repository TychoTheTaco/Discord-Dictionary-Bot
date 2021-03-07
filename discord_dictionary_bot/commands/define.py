import io
from contextlib import redirect_stderr
import argparse
import re
import sqlite3 as sql

import discord
from google.cloud import texttospeech
from discord_slash import SlashContext
from typing import Tuple
from bs4 import BeautifulSoup
import requests

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

            self._get_available_languages()

    async def execute(self, context: Context, args: tuple) -> None:
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
            await utils.send_or_dm(f'Invalid arguments!\nUsage: `{self.name} {self.usage}`', context.channel, user=context.author)
            return

        # Extract word from arguments
        word = ' '.join(args.word).strip()

        # Make sure this could be a word
        if not self._is_valid_word(word):
            await utils.send_or_dm('That\'s not a word', context.channel, context.author)
            return

        if self._add_request(context.author, word, context.channel, False, args.text_to_speech, args.language):
            await utils.send_or_dm(':white_check_mark: Word added to queue.', context.channel, context.author)

    def _validate_slash_command_arguments(self, slash_context, args: tuple) -> Tuple[str, dict]:
        results = {}

        word = args[0]

        index = 1

        # Text to speech
        if len(args) > index:
            if type(args[index]) is bool:
                results['text_to_speech'] = args[index]
                index += 1

        if 'text_to_speech' not in results:
            results['text_to_speech'] = False

        # Language
        if len(args) > index:
            if type(args[index]) is str:
                results['language'] = args[index]
                index += 1

        if 'language' not in results:
            results['language'] = self.client.properties.get(slash_context.channel, 'language')

        return word, results

    async def execute_slash_command(self, slash_context: SlashContext, args: tuple) -> None:
        word, kwargs = self._validate_slash_command_arguments(slash_context, args)

        # Make sure this could be a word
        if not self._is_valid_word(word):
            await slash_context.send(send_type=3, content='That\'s not a word', hidden=True)
            return

        self._add_request(slash_context.author, word, slash_context.channel, False, **kwargs)
        await slash_context.send(content=f'Added **{word}** to queue.', send_type=3)  # TODO: Sometimes this gets sent after the definition request was already processed

    def _is_valid_word(self, word) -> bool:
        pattern = re.compile(r'^[a-zA-Z-\' ]+$')
        return pattern.search(word) is not None

    def _add_request(self, user: discord.User, word, channel: discord.abc.Messageable, reverse, text_to_speech, language):

        # Check for text-to-speech override
        text_to_speech_property = self.client.properties.get(channel, 'text_to_speech')
        if text_to_speech_property == 'force' and isinstance(user, discord.Member):
            text_to_speech = user.voice is not None
        elif text_to_speech_property == 'disable':
            text_to_speech = False

        # Get voice code from language
        if text_to_speech:
            language = self._get_voice_code(language)

        # Add to definition queue
        self._definition_response_manager.add(DefinitionRequest(user, word, channel, reverse=reverse, text_to_speech=text_to_speech, language=language))

    def _get_voice_code(self, language) -> str:
        connection = sql.connect('database.db')
        cursor = connection.cursor()

        q = 'ORDER BY CASE voice_type WHEN "WaveNet" THEN 0 ELSE 1 END, CASE voice_gender WHEN "FEMALE" THEN 0 ELSE 1 END ASC'

        # TODO: sort by wavenet first and female first
        results = cursor.execute(f'SELECT * FROM voices WHERE voice_code LIKE ? {q}', (language,))
        for r in results:
            print('1:', r)
            return r[0]

        results = cursor.execute(f'SELECT * FROM voices WHERE language_code LIKE ? {q}', (language,))
        for r in results:
            print('2:', r)
            return r[0]

        results = cursor.execute(f'SELECT * FROM voices WHERE language_name LIKE ? {q}', (language,))
        for r in results:
            print('3:', r)
            return r[0]

        results = cursor.execute(f'SELECT * FROM voices WHERE language_region LIKE ? {q}', (language,))
        for r in results:
            print('4:', r)
            return r[0]

        connection.close()

        return ''

    def _get_available_languages(self):

        # TODO: error handling
        request = requests.get('https://cloud.google.com/text-to-speech/docs/voices')
        soup = BeautifulSoup(request.content, 'lxml')
        languages_table = soup.find('div', attrs={'class': 'devsite-article-body clearfix'}).table

        connection = sql.connect('database.db')
        cursor = connection.cursor()

        # Create table
        cursor.execute(
            'CREATE TABLE IF NOT EXISTS voices (voice_code text UNIQUE, language_code text, language_name text, language_region text, voice_type text, voice_gender text)')

        # Add languages
        for row in languages_table.find_all('tr')[1:]:
            columns = row.find_all('td')

            # Get language name and region
            pattern = re.compile(r'(\w+)(?: \((\w+)\))?')
            match = pattern.match(columns[0].text)
            if match:
                language_name = match.group(1)
                region = match.group(2)

                voice_type = columns[1].text
                language_code = columns[2].text
                voice_code = columns[3].text
                voice_gender = columns[4].text

                cursor.execute(f'INSERT OR IGNORE INTO voices VALUES (?, ?, ?, ?, ?, ?)', (voice_code, language_code, language_name, region, voice_type, voice_gender))

        connection.commit()
        connection.close()

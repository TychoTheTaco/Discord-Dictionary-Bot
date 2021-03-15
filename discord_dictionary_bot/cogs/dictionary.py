import argparse
import io
import subprocess

from discord.ext import commands
from google.cloud import texttospeech

from dictionary_api import DictionaryAPI
from typing import Union, Optional
from pathlib import Path
import collections
import requests
from bs4 import BeautifulSoup
import sqlite3 as sql
import re
import discord
from discord_slash import SlashContext, cog_ext
import asyncio
import logging
import contextlib
from exceptions import InsufficientPermissionsException
from google.cloud.texttospeech_v1.services.text_to_speech.transports.grpc import TextToSpeechGrpcTransport

# Set up logging
logger = logging.getLogger(__name__)


class DefinitionRequest:

    def __init__(self, user: discord.User, word: str, text_channel: discord.abc.Messageable, reverse=False, text_to_speech=False, language='en-us'):
        self.user = user
        self.voice_channel = user.voice.channel if isinstance(user, discord.Member) and user.voice is not None else None
        self.word = word
        self.text_channel = text_channel
        self.reverse = reverse
        self.text_to_speech = text_to_speech
        self.language = language

    def __repr__(self):
        return f'{{word: "{self.word}", reverse: {self.reverse}, text_to_speech: {self.text_to_speech}, language: "{self.language}"}}'


def convert(source: bytes, ffmpeg_path='ffmpeg'):
    # Start ffmpeg process
    process = subprocess.Popen(
        [ffmpeg_path, '-i', 'pipe:0', '-ac', '2', '-f', 's16le', 'pipe:1', '-loglevel', 'panic'],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE
    )

    # Pipe input and wait for output
    output = process.communicate(source)

    return output[0]


def text_to_speech_pcm(text, language='en-us', gender=texttospeech.SsmlVoiceGender.NEUTRAL) -> bytes:
    # Create a text-to-speech client with maximum receive size of 24MB. This limit can be adjusted if necessary. It needs to be specified because the default of 4MB is not enough for some definitions.
    channel = TextToSpeechGrpcTransport.create_channel(options=[('grpc.max_receive_message_length', 24 * 1024 * 1024)])
    transport = TextToSpeechGrpcTransport(channel=channel)
    client = texttospeech.TextToSpeechClient(transport=transport)

    language_components = language.split('-')
    language_code = '-'.join(language_components[:2])
    name = None
    if len(language_components) == 4:
        name = language

    # Build the voice request
    voice = texttospeech.VoiceSelectionParams(
        language_code=language_code, ssml_gender=gender, name=name
    )

    # Select the type of audio file you want returned
    audio_config = texttospeech.AudioConfig(
        audio_encoding=texttospeech.AudioEncoding.LINEAR16,
        sample_rate_hertz=48000
    )

    # Set the text input to be synthesized
    synthesis_input = texttospeech.SynthesisInput(text=text)

    # Request text-to-speech data
    response = client.synthesize_speech(input=synthesis_input, voice=voice, audio_config=audio_config)
    return response.audio_content


async def send_maybe_hidden(context: Union[commands.Context, SlashContext], text: Optional[str] = None, **kwargs):
    if isinstance(context, SlashContext):
        return await context.send(text, hidden=True, **kwargs)
    return await context.send(text, **kwargs)


class DefinitionResponseManager:

    def __init__(self, bot: commands.Bot, guild: discord.Guild):
        self._bot = bot
        self._guild = guild

        # Each text channel will have its own request queue to allow simultaneous responses across channels
        self._request_queues = {}

        # Keep track of which voice channels we need to respond to. This way we can leave the channel only when we have finished all requests for that channel
        self._voice_channels = collections.defaultdict(int)

        self._voice_channel_locks = {}

        # Each guild will have a lock to ensure that we can only be connected to 1 voice channel at a time
        self._guild_voice_channel_locks = {}


class Dictionary(commands.Cog):

    def __init__(self, bot: commands.Bot, dictionary_api: DictionaryAPI, ffmpeg_path: Union[str, Path]):
        self._bot = bot
        self._dictionary_api = dictionary_api
        self._ffmpeg_path = ffmpeg_path

        # Create and populate table of supported text-to-speech voices
        self._create_voices_table()

        # Each text channel will have its own request queue to allow simultaneous responses across channels
        self._request_queues = {}

        # Keep track of which voice channels we need to respond to. This way we can leave the channel only when we have finished all requests for that channel
        self._voice_channels = collections.defaultdict(int)

        self._voice_channel_locks = {}

        # Each guild will have a lock to ensure that we can only be connected to 1 voice channel at a time
        self._guild_voice_channel_locks = {}

    @commands.command(name='define', aliases=['d'])
    async def define(self, context: commands.Context, *args):
        word, text_to_speech, language = await self._parse_define_or_befine(context, *args)
        await self._define_or_befine(context, word, False, text_to_speech, language)

    @cog_ext.cog_slash(
        name='define',
        description='Gets the definition of a word and optionally reads it out to you.',
        options=[
            {
                'name': 'word',
                'description': 'The word to define.',
                'type': 3,
                'required': True
            },
            {
                'name': 'text_to_speech',
                'description': 'Reads the definition to you.',
                'type': 5
            },
            {
                'name': 'language',
                'description': 'The language to use when reading the definition.',
                'type': 3,
            }
        ]
    )
    async def slash_define(self, context: SlashContext, word: str, text_to_speech: bool = False, language: str = 'English'):
        await context.respond(True)
        await self._define_or_befine(context, word, False, text_to_speech, language)

    @commands.command(name='befine', aliases=['b'], hidden=True)
    async def befine(self, context: commands.Context, *args):
        word, text_to_speech, language = await self._parse_define_or_befine(context, *args)
        await self._define_or_befine(context, word, True, text_to_speech, language)

    async def _parse_define_or_befine(self, context: commands.Context, *args) -> (str, bool, str):
        # Get default language
        preferences_cog = self._bot.get_cog('preferences')
        default_language = preferences_cog.scoped_property_manager.get('language', context.channel)

        # Parse arguments
        try:
            parser = argparse.ArgumentParser()
            parser.add_argument('word', nargs='+')
            parser.add_argument('-v', action='store_true', default=False, dest='text_to_speech')
            parser.add_argument('-lang', '-l', dest='language', default=default_language)

            # Parse arguments but suppress stderr output
            stderr_stream = io.StringIO()
            with contextlib.redirect_stderr(stderr_stream):
                args = parser.parse_args(args)
        except SystemExit:
            raise commands.errors.ArgumentParsingError("Invalid arguments!")

        # Extract word from arguments
        word = ' '.join(args.word).strip()

        return word, args.text_to_speech, args.language

    async def _define_or_befine(self, context: Union[commands.Context, SlashContext], word: str, reverse: bool = False, text_to_speech: bool = False, language: str = 'English'):

        # Make sure this could be a word
        if not self._is_valid_word(word):
            await send_maybe_hidden(context, 'That\'s not a word.')
            return

        # Get current voice channel
        voice_channel = context.author.voice.channel if context.author.voice is not None else None

        # Make sure that the user that requested this definition is in a voice channel if text-to-speech is enabled
        if text_to_speech and voice_channel is None:
            await send_maybe_hidden(context, 'You must be in a voice channel to use text-to-speech!')
            return

        # Check for text-to-speech override
        preferences_cog = self._bot.get_cog('preferences')
        text_to_speech_property = preferences_cog.scoped_property_manager.get('text_to_speech', context.channel)
        if text_to_speech_property == 'force' and voice_channel is not None:
            text_to_speech = True
        elif text_to_speech_property == 'disable':
            text_to_speech = False

        # Get voice code from language argument
        if text_to_speech:
            voice_code = self._get_voice_code(language)
            if voice_code is None:
                await send_maybe_hidden(context, f'Could not find a language matching `{language}`!')
                return
            language = voice_code

        # Add request to queue
        if context.channel not in self._request_queues:
            queue = asyncio.Queue()
            self._request_queues[context.channel] = queue
            task = asyncio.create_task(self._process_definition_requests(queue))

        if text_to_speech:
            if voice_channel not in self._voice_channels:
                self._voice_channels[voice_channel] = 0
                self._voice_channel_locks[voice_channel] = asyncio.Lock()
            self._voice_channels[voice_channel] += 1

        await self._request_queues[context.channel].put(DefinitionRequest(context.author, word, context.channel, reverse, text_to_speech, language))

        # Acknowledge
        await context.send(f'Added **{word}** to queue.')

    @staticmethod
    def _is_valid_word(word) -> bool:
        pattern = re.compile(r'^[a-zA-Z-\' ]+$')
        return pattern.search(word) is not None

    @staticmethod
    def create_reply(word, definitions, reverse=False) -> (str, str):
        if reverse:
            word = word[::-1]
        reply = f'__**{word}**__\n'
        tts_input = f'{word}, '
        for i, definition in enumerate(definitions):
            word_type = definition['word_type']
            definition_text = definition['definition']

            if reverse:
                word_type = word_type[::-1]
                definition_text = definition_text[::-1]

            reply += f'**[{i + 1}]** ({word_type})\n' + definition_text + '\n'
            tts_input += f' {i + 1}, {word_type}, {definition_text}'

        return reply, tts_input

    def _get_text_to_speech(self, tts_input: str, language: str) -> io.BytesIO:
        result = io.BytesIO()

        try:
            text_to_speech_bytes = text_to_speech_pcm(tts_input, language=language)
        except Exception as e:
            logger.error(f'Failed to generate text-to-speech data: {e}. You might be using an invalid language: "{language}"')
            return result

        # Convert to proper format
        text_to_speech_bytes = convert(text_to_speech_bytes, ffmpeg_path=self._ffmpeg_path)
        result.write(text_to_speech_bytes)
        result.seek(0)

        return result

    async def _process_definition_requests(self, queue: asyncio.Queue):
        # This lock is used to ensure that only 1 definition request is processed at a time (per text channel)
        master_lock = asyncio.Lock()

        while True:

            # Wait for an item to enter the queue
            logger.debug(f'[{self}] Waiting for more requests...')
            definition_request: DefinitionRequest = await queue.get()
            logger.debug(f'[{self}] Processing request: {definition_request}')

            word = definition_request.word
            text_to_speech = definition_request.text_to_speech
            voice_channel = definition_request.voice_channel

            # Get definition
            definitions = await self._dictionary_api.define(word)

            if len(definitions) == 0:
                await master_lock.acquire()
                await definition_request.text_channel.send('I couldn\'t find any definitions for that word.')
                master_lock.release()
                continue

            # Prepare response text and text-to-speech input
            reply, text_to_speech_input = self.create_reply(word, definitions, reverse=definition_request.reverse)

            if text_to_speech:

                # Get text-to-speech data
                text_to_speech_bytes = self._get_text_to_speech(text_to_speech_input, language=definition_request.language)

                await master_lock.acquire()

                # Check if we got valid text-to-speech data
                if text_to_speech_bytes.getbuffer().nbytes <= 0:
                    await definition_request.text_channel.send('There was a problem generating the text-to-speech!')
                    master_lock.release()
                    continue

                # Join the voice channel
                try:
                    await self._voice_channel_locks[voice_channel].acquire()
                    voice_client = await self._join_voice_channel(voice_channel)
                except InsufficientPermissionsException as e:
                    self._voice_channel_locks[voice_channel].release()
                    await definition_request.text_channel.send(f'I don\'t have permission to join your voice channel! Please grant me the following permissions: ' + ', '.join(f'`{x}`' for x in e.permissions) + '.')
                    master_lock.release()
                    continue

                # Temporary fix for (https://github.com/TychoTheTaco/Discord-Dictionary-Bot/issues/1)
                await asyncio.sleep(2.5)

                # Send text chat reply
                await definition_request.text_channel.send(reply)

                # Speak
                def after(error):

                    if error is not None:
                        logger.error(f'An error occurred while playing audio: {error}')

                    # Update voice channel map
                    self._voice_channels[voice_channel] -= 1

                    # Disconnect from the voice channel if we don't need it anymore
                    if self._voice_channels[voice_channel] == 0:
                        asyncio.run_coroutine_threadsafe(self._leave_voice_channel(voice_channel), self._bot.loop)

                    self._voice_channel_locks[voice_channel].release()
                    master_lock.release()

                voice_client.play(discord.PCMAudio(text_to_speech_bytes), after=after)

            else:
                await master_lock.acquire()
                await definition_request.text_channel.send(reply)
                master_lock.release()

    @commands.command(name='next', aliases=['n'])
    async def next(self, context: commands.Context):
        print('next')

    @commands.command(name='stop', aliases=['s'])
    async def stop(self, context: commands.Context):
        pass

    @commands.command(name='voices', aliases=['voice', 'v'], help='Shows the list of supported voices for text to speech.')
    async def voices(self, context: commands.Context):
        await self._voices(context)

    @cog_ext.cog_slash(name='voices')
    async def slash_voices(self, context: SlashContext):
        await context.respond(True)
        await self._voices(context)

    async def _voices(self, context: Union[commands.Context, SlashContext]):
        supported_voices_url = 'https://cloud.google.com/text-to-speech/docs/voices'

        # Check if we can embed links in this channel
        if isinstance(context.channel, discord.DMChannel) or context.channel.guild.me.permissions_in(context.channel).embed_links:

            # Send reply
            e = discord.Embed()
            e.title = 'Supported Voices'
            e.url = supported_voices_url

            await send_maybe_hidden(context, embed=e)

        else:

            # Connect to database
            connection = sql.connect('database.db')
            cursor = connection.cursor()

            reply = '__Supported Voices__\n'

            results = cursor.execute(f'SELECT DISTINCT (language_name) FROM voices ORDER BY language_name')
            for result in results:
                reply += f'{result[0]}\n'

            connection.close()

            await send_maybe_hidden(context, reply)

    @staticmethod
    def _create_voices_table():

        # Get supported languages from HTML
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

    @staticmethod
    def _get_voice_code(language: str) -> Optional[str]:
        """
        Get the voice code that best matches the given language. Voice codes are matched in the following priority:
        1) voice code
        2) language code
        3) language name
        4) language region
        Additionally, WaveNet voices are prioritized over Standard voices and female voices are prioritized over male voices.
        :param language:
        :return: A string representing a valid voice code that can be used with the Google Text-to-Speech library.
        """

        # Connect to database
        connection = sql.connect('database.db')
        cursor = connection.cursor()

        # Prepare queries
        q = 'ORDER BY CASE voice_type WHEN "WaveNet" THEN 0 ELSE 1 END, CASE voice_gender WHEN "FEMALE" THEN 0 ELSE 1 END ASC'
        queries = (
            f'SELECT * FROM voices WHERE voice_code LIKE ? {q}',
            f'SELECT * FROM voices WHERE language_code LIKE ? {q}',
            f'SELECT * FROM voices WHERE language_name LIKE ? {q}',
            f'SELECT * FROM voices WHERE language_region LIKE ? {q}'
        )

        # Return first value that matches a query
        for query in queries:
            results = cursor.execute(query, (language,))
            for result in results:
                connection.close()
                return result[0]

        connection.close()

        return None

    async def _join_voice_channel(self, voice_channel: discord.VoiceChannel) -> discord.VoiceProtocol:
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
        for voice_client in self._bot.voice_clients:
            if voice_client.channel == voice_channel:
                return voice_client

        # Connect to the voice channel
        return await voice_channel.connect()

    async def _leave_voice_channel(self, voice_channel: discord.VoiceChannel) -> None:
        """
        Leave the specified voice channel if we were connected to it.
        :param voice_channel: The voice channel to leave.
        """
        for voice_client in self._bot.voice_clients:
            if voice_client.channel == voice_channel:
                await voice_client.disconnect()

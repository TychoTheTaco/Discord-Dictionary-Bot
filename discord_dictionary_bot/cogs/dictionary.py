import argparse
import io
import subprocess
import asyncio
import logging
import contextlib
import sqlite3 as sql
import re
from typing import Union, Optional
from pathlib import Path
import threading
import datetime
import json

from discord.ext import commands
from google.cloud import texttospeech, bigquery
import requests
from bs4 import BeautifulSoup
import discord
from discord_slash import SlashContext, cog_ext
from google.cloud.texttospeech_v1.services.text_to_speech.transports.grpc import TextToSpeechGrpcTransport

from dictionary_api import DictionaryAPI
from exceptions import InsufficientPermissionsException

# Set up logging
logger = logging.getLogger(__name__)


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


def catch_exceptions(function):
    """
    This decorator will catch and log all exceptions thrown in the decorated function.
    :param function:
    :return:
    """

    def f(*args, **kwargs):
        try:
            function(*args, *kwargs)
        except Exception as e:
            logger.exception(f'Exception: {e}')

    return f


def run_on_another_thread(function):
    """
    This decorator will run the decorated function in another thread, starting it immediately.
    :param function:
    :return:
    """

    def f(*args, **kargs):
        threading.Thread(target=function, args=[*args, *kargs]).start()

    return f


@run_on_another_thread
@catch_exceptions
def send_analytics(word, reverse, text_to_speech, language, text_channel) -> None:
    # Ignore dev server
    #if isinstance(text_channel, discord.TextChannel) and text_channel.guild.id in [454852632528420876, 799455809297842177]:
    #    logger.info(f'Ignoring analytics submission for development server.')
    #    return

    client = bigquery.Client()
    job_config = bigquery.LoadJobConfig(
        schema=[
            bigquery.SchemaField("word", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("reverse", "BOOLEAN", mode="REQUIRED"),
            bigquery.SchemaField("text_to_speech", "BOOLEAN", mode="REQUIRED"),
            bigquery.SchemaField("language", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("guild_id", "INTEGER"),
            bigquery.SchemaField("channel_id", "INTEGER"),
            bigquery.SchemaField("time", "TIMESTAMP"),
        ],
        source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON,
        autodetect=True
    )

    data = {
        'word': word,
        'reverse': reverse,
        'text_to_speech': text_to_speech,
        'language': language,
        'guild_id': None,
        'channel_id': None,
        'time': datetime.datetime.now().isoformat()
    }

    if isinstance(text_channel, discord.TextChannel):
        data['guild_id'] = text_channel.guild.id
        data['channel_id'] = text_channel.id
    elif isinstance(text_channel, discord.DMChannel):
        data['channel_id'] = text_channel.id

    data_as_file = io.StringIO(json.dumps(data))
    job = client.load_table_from_file(data_as_file, 'formal-scout-290305.analytics.definition_requests', job_config=job_config)

    try:
        job.result()  # Waits for the job to complete.
    except Exception as e:
        raise Exception(f'Failed BigQuery upload job. Exception: {e} Errors: {job.errors}')


class Dictionary(commands.Cog):

    DEFINE_COMMAND_DESCRIPTION = 'Gets the definition of a word and optionally reads it out to you.'
    STOP_COMMAND_DESCRIPTION = 'Makes the bot stop talking.'
    LANGUAGES_COMMAND_DESCRIPTION = 'Shows a list of supported voices for text to speech.'

    def __init__(self, bot: commands.Bot, dictionary_api: DictionaryAPI, ffmpeg_path: Union[str, Path]):
        self._bot = bot
        self._dictionary_api = dictionary_api
        self._ffmpeg_path = ffmpeg_path

        # Create and populate a table of supported text-to-speech voices
        self._create_voices_table()

        # Each guild will have a lock to ensure that we only join 1 voice channel at a time
        self._guild_locks = {}

        # This dict keeps track of how many definition requests need the corresponding voice channel. This way we can leave the channel only when we have finished all requests
        # for that channel.
        self._voice_channels = {}

    @commands.command(name='define', aliases=['d'], help=DEFINE_COMMAND_DESCRIPTION)
    async def define(self, context: commands.Context, *args):
        async with context.typing():
            word, text_to_speech, language = await self._parse_define_or_befine(context, *args)
            await self._define_or_befine(context, word, False, text_to_speech, language)

    @cog_ext.cog_slash(
        name='define',
        description=DEFINE_COMMAND_DESCRIPTION,
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
    async def slash_define(self, context: SlashContext, word: str, text_to_speech: bool = False, language: Optional[str] = None):
        # Get default language
        if language is None:
            preferences_cog = self._bot.get_cog('Preferences')
            language = preferences_cog.scoped_property_manager.get('language', context.channel)

        await self._define_or_befine(context, word, False, text_to_speech, language)

    @commands.command(name='befine', aliases=['b'], hidden=True)
    async def befine(self, context: commands.Context, *args):
        async with context.typing():
            word, text_to_speech, language = await self._parse_define_or_befine(context, *args)
            await self._define_or_befine(context, word, True, text_to_speech, language)

    async def _parse_define_or_befine(self, context: commands.Context, *args) -> (str, bool, str):
        # Get default language
        preferences_cog = self._bot.get_cog('Preferences')
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
        voice_channel = context.author.voice.channel if isinstance(context.author, discord.Member) and context.author.voice is not None else None

        # Make sure that the user that requested this definition is in a voice channel if text-to-speech is enabled
        if text_to_speech and voice_channel is None:
            await send_maybe_hidden(context, 'You must be in a voice channel to use text-to-speech!')
            return

        # Check for text-to-speech override
        preferences_cog = self._bot.get_cog('Preferences')
        text_to_speech_property = preferences_cog.scoped_property_manager.get('text_to_speech', context.channel)
        if text_to_speech_property == 'force' and voice_channel is not None:
            text_to_speech = True
        elif text_to_speech_property == 'disable':
            text_to_speech = False

        if text_to_speech:

            # Get voice code from language argument
            voice_code = self._get_voice_code(language)
            if voice_code is None:
                await send_maybe_hidden(context, f'Could not find a language matching `{language}`!')
                return
            language = voice_code

            # Increment counter for this voice channel
            if voice_channel not in self._voice_channels:
                self._voice_channels[voice_channel] = 0
            if voice_channel is not None:
                self._voice_channels[voice_channel] += 1

            if context.guild not in self._guild_locks:
                self._guild_locks[context.guild] = asyncio.Lock()

        if isinstance(context, SlashContext):
            await context.respond()

        logger.info(f'Processing definition request: {{word: "{word}", reverse: {reverse}, text_to_speech: {text_to_speech}, language: "{language}"}}')
        send_analytics(word, reverse, text_to_speech, language, context.channel)

        # Get definition
        definitions = await self._dictionary_api.define(word)

        if len(definitions) == 0:
            reply = f'__**{word}**__\nI couldn\'t find any definitions for that word.'
            if text_to_speech:
                await self._say(reply, context, voice_channel, language, f'{word}. I couldn\'t find any definitions for that word.')
            else:
                await context.send(reply)
            return

        # Prepare response text and text-to-speech input
        reply, text_to_speech_input = self.create_reply(word, definitions, reverse=reverse)

        if text_to_speech:
            await self._say(reply, context, voice_channel, language, text_to_speech_input)
        else:
            await context.send(reply)

    async def _say(self, text: str, context: Union[commands.Context, SlashContext], voice_channel, language, text_to_speech_input=None):

        # Get text-to-speech data
        text_to_speech_bytes = self._get_text_to_speech(text_to_speech_input, language=language)

        # Check if we got valid text-to-speech data
        if text_to_speech_bytes.getbuffer().nbytes <= 0:
            await context.send('There was a problem generating the text-to-speech!')
            return

        # Join the voice channel
        try:
            await self._guild_locks[context.guild].acquire()
            voice_client = await self._join_voice_channel(voice_channel)
        except InsufficientPermissionsException as e:
            self._guild_locks[context.guild].release()
            await context.send(
                f'I don\'t have permission to join your voice channel! Please grant me the following permissions: ' + ', '.join(f'`{x}`' for x in e.permissions) + '.')
            return

        # Temporary fix for (https://github.com/TychoTheTaco/Discord-Dictionary-Bot/issues/1)
        await asyncio.sleep(2.5)

        # Send text chat reply
        await context.send(text)

        # Create a callback to be invoked when the bot is finished playing audio
        def after(error):

            # A nested async function is used here to ensure that the bot leaves the voice channel before releasing the associated locks
            async def after_coroutine(error):

                if error is not None:
                    logger.error(f'An error occurred while playing audio: {error}')

                # Update voice channel map
                self._voice_channels[voice_channel] -= 1

                # Disconnect from the voice channel if we don't need it anymore
                if self._voice_channels[voice_channel] <= 0:
                    await self._leave_voice_channel(voice_channel)

                self._guild_locks[context.guild].release()

            asyncio.run_coroutine_threadsafe(after_coroutine(error), self._bot.loop)

        # Speak
        voice_client.play(discord.PCMAudio(text_to_speech_bytes), after=after)

    @staticmethod
    def _is_valid_word(word) -> bool:
        pattern = re.compile(r'^[a-zA-Z-\' ]+$')
        return pattern.search(word) is not None

    async def _join_voice_channel(self, voice_channel: discord.VoiceChannel) -> discord.VoiceProtocol:
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
        for voice_client in self._bot.voice_clients:
            if voice_client.channel == voice_channel:
                await voice_client.disconnect()

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

    @commands.command(name='stop', aliases=['s'], help=STOP_COMMAND_DESCRIPTION)
    async def stop(self, context: commands.Context):
        for voice_client in self._bot.voice_clients:
            if voice_client == context.voice_client:
                await self._stop(context, voice_client)
                return

    @cog_ext.cog_slash(name='stop', description=STOP_COMMAND_DESCRIPTION)
    async def slash_stop(self, context: SlashContext):
        await context.respond(True)

        # Get voice channel of current user
        voice_channel = context.author.voice.channel if isinstance(context.author, discord.Member) and context.author.voice is not None else None

        # Get voice client
        for voice_client in self._bot.voice_clients:
            if voice_client.channel == voice_channel:
                await self._stop(context, voice_client)
                return

    async def _stop(self, context: Union[commands.Context, SlashContext], voice_client: discord.VoiceClient):
        voice_client.stop()
        await context.send('Okay, I\'ll be quiet.')

    @commands.command(name='voices', aliases=['voice', 'v'], help=LANGUAGES_COMMAND_DESCRIPTION)
    async def voices(self, context: commands.Context):
        await self._voices(context)

    @cog_ext.cog_slash(name='voices', description=LANGUAGES_COMMAND_DESCRIPTION)
    async def slash_voices(self, context: SlashContext):
        await context.respond()
        await self._voices(context)

    async def _voices(self, context: Union[commands.Context, SlashContext]):
        supported_voices_url = 'https://cloud.google.com/text-to-speech/docs/voices'

        # Check if we can embed links in this channel
        if isinstance(context.channel, discord.DMChannel) or context.channel.guild.me.permissions_in(context.channel).embed_links:

            # Send reply
            e = discord.Embed()
            e.title = 'Supported Voices'
            e.url = supported_voices_url

            await context.send(embed=e)

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

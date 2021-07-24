import argparse
import io
import asyncio
import logging
import contextlib
import sqlite3 as sql
import re
from typing import Union, Optional, Dict
from pathlib import Path
import html

from discord.ext import commands
from google.cloud import texttospeech
import requests
from bs4 import BeautifulSoup
import discord
from discord_slash import SlashContext, cog_ext
from google.cloud.texttospeech_v1.services.text_to_speech.transports.grpc import TextToSpeechGrpcTransport
from google.cloud import translate_v2 as translate

from ..dictionary_api import DictionaryAPI, SequentialDictionaryAPI
from ..exceptions import InsufficientPermissionsException
from .. import utils
from ..analytics import log_definition_request

# Set up logging
logger = logging.getLogger(__name__)


async def convert(source: bytes, ffmpeg_path='ffmpeg'):
    # Start ffmpeg process
    process = await asyncio.create_subprocess_shell(
        f'"{ffmpeg_path}" -i pipe:0 -ac 2 -f s16le pipe:1 -loglevel panic',
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )

    # Pipe input and wait for output
    output = await process.communicate(source)

    return output[0]


def text_to_speech_pcm(text, language='en-us', gender=texttospeech.SsmlVoiceGender.NEUTRAL) -> bytes:
    # Create a text-to-speech client with maximum receive size of 24MB. This limit can be adjusted if necessary. It needs to be specified
    # because the default of 4MB is not enough for some definitions.
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


class Dictionary(commands.Cog):
    DEFINE_COMMAND_DESCRIPTION = 'Gets the definition of a word and optionally reads it out to you.'
    STOP_COMMAND_DESCRIPTION = 'Makes the bot stop talking.'
    TRANSLATE_COMMAND_DESCRIPTION = 'Translate a message from one language to another.'
    TRANSLATE_MAX_MESSAGE_LENGTH = 200

    def __init__(self, bot: commands.Bot, dictionary_apis: [DictionaryAPI], ffmpeg_path: Union[str, Path]):
        self._bot = bot
        self._dictionary_apis = {api.id(): api for api in dictionary_apis}
        self._ffmpeg_path = Path(ffmpeg_path)

        # Create and populate a table of supported text-to-speech voices
        self._create_voices_table()

        # Each guild will have a lock to ensure that we only join 1 voice channel at a time
        self._guild_locks = {}

        # This dict keeps track of how many definition requests need the corresponding voice channel. This way we can leave the channel
        # only when we have finished all requests for that channel.
        self._voice_channels = {}

        # Client used for translations
        self._translate_client = translate.Client()

        # Get supported languages for translation
        self._language_to_voice_map = {}
        self._languages = []
        for x in self._translate_client.get_languages(target_language='en'):
            vc = self._get_voice_code(x['language'])
            if vc is None:
                vc = self._get_voice_code(x['name'].split(' ')[0])
            self._language_to_voice_map[x['language']] = vc
            self._languages.append(x)

        # Override some voices
        override_voices = {
            'en': 'en-US-Wavenet-C'
        }
        for key, value in override_voices.items():
            if key in self._language_to_voice_map:
                self._language_to_voice_map[key] = value

    def _translate(self, text: str, target_language: str, source_language: str = None):
        result = self._translate_client.translate(text, target_language=target_language, source_language=source_language)
        translated_text = html.unescape(result['translatedText'])

        if source_language is None:
            return translated_text, result['detectedSourceLanguage']
        else:
            return translated_text

    @commands.command(name='define', aliases=['d'], help=DEFINE_COMMAND_DESCRIPTION, usage='[-v] [-lang <language>] <word>')
    async def define(self, context: commands.Context, *args):
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
            preferences_cog = self._bot.get_cog('Settings')
            language = preferences_cog.scoped_property_manager.get('language', context.channel)

        await self._define_or_befine(context, word, False, text_to_speech, language)

    @commands.command(name='befine', aliases=['b'], hidden=True)
    async def befine(self, context: commands.Context, *args):
        word, text_to_speech, language = await self._parse_define_or_befine(context, *args)
        await self._define_or_befine(context, word, True, text_to_speech, language)

    async def _parse_define_or_befine(self, context: commands.Context, *args) -> (str, bool, str):
        # Get default language
        preferences_cog = self._bot.get_cog('Settings')
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
            await utils.reply_maybe_hidden(context, 'That\'s not a word.')
            return

        # Get current voice channel
        voice_channel = context.author.voice.channel if isinstance(context.author, discord.Member) and context.author.voice is not None else None

        # Make sure that the user that requested this definition is in a voice channel if text-to-speech is enabled
        if text_to_speech and voice_channel is None:
            await utils.reply_maybe_hidden(context, 'You must be in a voice channel to use text-to-speech!')
            return

        # Check for text-to-speech override
        preferences_cog = self._bot.get_cog('Settings')
        text_to_speech_property = preferences_cog.scoped_property_manager.get('text_to_speech', context.channel)
        if text_to_speech_property == 'force' and voice_channel is not None:
            text_to_speech = True
        elif text_to_speech_property == 'disable':
            text_to_speech = False

        # Get voice code from language argument
        language_code = self._get_language_code(language)
        if language_code is None:
            await utils.reply_maybe_hidden(context, f'Could not find a language matching `{language}`!')
            return

        # Check if this language has a supported voice
        if self._language_to_voice_map[language_code] is None:
            text_to_speech = False
            await utils.reply_maybe_hidden(context, 'I can\'t speak that language!')

        if text_to_speech:

            voice_code = self._language_to_voice_map[language_code]

            # Increment counter for this voice channel
            if voice_channel not in self._voice_channels:
                self._voice_channels[voice_channel] = 0
            if voice_channel is not None:
                self._voice_channels[voice_channel] += 1

            if context.guild not in self._guild_locks:
                self._guild_locks[context.guild] = asyncio.Lock()

        if isinstance(context, SlashContext):
            await context.defer()

        logger.info(f'Processing definition request: {{word: "{word}", reverse: {reverse}, text_to_speech: {text_to_speech}, language: "{language_code}"}}')

        # Get dictionary api
        dictionary_api_property = preferences_cog.scoped_property_manager.get('dictionary_apis', context.channel)
        dictionary_api = SequentialDictionaryAPI([self._dictionary_apis[api_id] for api_id in dictionary_api_property if api_id in self._dictionary_apis])

        if isinstance(context, SlashContext):
            cm = contextlib.AsyncExitStack()
        else:
            cm = context.typing()

        async with cm:

            # Translate the word to english
            if preferences_cog.scoped_property_manager.get('auto_translate', context.channel):
                word, detected_source_language = self._translate(word, 'en')
            else:
                detected_source_language = 'en'

            # Get definition
            definitions, definition_source = await dictionary_api.define_with_source(word)

            if len(definitions) == 0:
                reply = f'__**{word}**__\nI couldn\'t find any definitions for that word.'
                if text_to_speech:
                    await self._say(reply, context, voice_channel, language_code, f'{word}. I couldn\'t find any definitions for that word.')
                else:
                    await context.send(reply)
                return

            # Record analytics only for valid words
            log_definition_request(word, reverse, text_to_speech, language, context)

            # Translate word and definitions to target language
            if language_code != 'en':
                word, _ = self._translate(word, language_code)
                for i in range(len(definitions)):
                    definitions[i]['word_type'], _ = self._translate(definitions[i]['word_type'], language_code)
                    definitions[i]['definition'], _ = self._translate(definitions[i]['definition'], language_code)

            # Prepare response text and text-to-speech input
            show_definition_source = preferences_cog.scoped_property_manager.get('show_definition_source', context.channel)
            reply, text_to_speech_input = self.create_reply(word, definitions, reverse=reverse, definition_source=definition_source.name if show_definition_source else None, detected_source_language=detected_source_language)

            if text_to_speech:
                await self._say(reply, context, voice_channel, voice_code, text_to_speech_input)
            else:
                await context.send(reply)

    async def _say(self, text: str, context: Union[commands.Context, SlashContext], voice_channel, language, text_to_speech_input=None):

        # Get text-to-speech data
        text_to_speech_bytes = await self._get_text_to_speech(text_to_speech_input, language=language)

        # Check if we got valid text-to-speech data
        if text_to_speech_bytes.getbuffer().nbytes <= 0:

            logger.error('There was a problem generating the text-to-speech!')
            await context.send('There was a problem generating the text-to-speech!')

            # Send text chat reply
            await context.send(text)

            # Update voice channel map
            self._voice_channels[voice_channel] -= 1

            # Disconnect from the voice channel if we don't need it anymore
            if self._voice_channels[voice_channel] <= 0:
                await self._leave_voice_channel(voice_channel)

        else:

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

    @commands.command(name='translate', aliases=['t'], help=TRANSLATE_COMMAND_DESCRIPTION, usage='[<target_language>] <message>')
    async def translate(self, context: commands.Context, *args):
        if len(args) < 2:
            raise commands.errors.ArgumentParsingError("Invalid arguments!")

        # Parse target language
        target_language = self._get_language_code(args[0])
        if target_language is None:
            await context.reply('Invalid language!', mention_author=False)
            return

        # Parse message
        message = ' '.join(args[1:])

        # Limit message length
        if len(message) > Dictionary.TRANSLATE_MAX_MESSAGE_LENGTH:
            await context.reply(f'Message is too long! Maximum length is {Dictionary.TRANSLATE_MAX_MESSAGE_LENGTH} characters.', mention_author=False)
            return

        translated_message, detected_language = self._translate(message, target_language=target_language)
        await context.reply(self._create_translate_reply(message, detected_language, translated_message, target_language), mention_author=False)

    @cog_ext.cog_slash(
        name='translate',
        description=TRANSLATE_COMMAND_DESCRIPTION,
        options=[
            {
                'name': 'target_language',
                'description': 'The language to translate to.',
                'type': 3,
                'required': True
            },
            {
                'name': 'message',
                'description': 'The message to translate.',
                'type': 3
            }
        ]
    )
    async def slash_translate(self, context: SlashContext, target_language: str, message: str):
        # Parse target language
        target_language = self._get_language_code(target_language)
        if target_language is None:
            await utils.reply_maybe_hidden(context, 'Invalid language!')
            return

        # Limit message length
        if len(message) > Dictionary.TRANSLATE_MAX_MESSAGE_LENGTH:
            await utils.reply_maybe_hidden(context, f'Message is too long! Maximum length is {Dictionary.TRANSLATE_MAX_MESSAGE_LENGTH} characters.')
            return

        translated_message, detected_language = self._translate(message, target_language=target_language)
        await context.send(self._create_translate_reply(message, detected_language, translated_message, target_language))

    def _create_translate_reply(self, message: str, source_language: str, translated_message: str, target_language: str):
        result = f'**__{self._get_language_name(source_language)}__**\n'
        result += message + '\n'
        result += f'**__{self._get_language_name(target_language)}__**\n'
        result += translated_message
        return result

    @staticmethod
    def _is_valid_word(word) -> bool:

        # Arbitrary maximum word size to hopefully prevent the bot from generating responses that are above Discord's message limit of 2000.
        if len(word) > 100:
            return False

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

    def create_reply(self, word, definitions, reverse=False, definition_source: Optional[str] = None, detected_source_language: str = 'en') -> (str, str):
        """
        Create a reply.
        :param word:
        :param definitions:
        :param reverse:
        :param definition_source:
        :return:
        """
        if reverse:
            word = word[::-1]

        reply = f'__**{word}**__'
        if detected_source_language != 'en':
            reply += f' ({self._get_language_name(detected_source_language)})'
        reply += '\n'
        tts_input = f'{word}, '

        for i, definition in enumerate(definitions):
            word_type = definition['word_type']
            definition_text = definition['definition']

            if reverse:
                word_type = word_type[::-1]
                definition_text = definition_text[::-1]

            reply += f'**[{i + 1}]** ({word_type})\n' + definition_text + '\n'
            tts_input += f' {i + 1}, {word_type}, {definition_text}'

        if definition_source is not None:
            reply += f'\n*Definitions provided by {definition_source}.*'

        return reply, tts_input

    async def _get_text_to_speech(self, tts_input: str, language: str) -> io.BytesIO:
        result = io.BytesIO()

        try:
            text_to_speech_bytes = text_to_speech_pcm(tts_input, language=language)
        except Exception as e:
            logger.error(f'Failed to generate text-to-speech data: {e}. You might be using an invalid language: "{language}"')
            return result

        # Convert to proper format
        text_to_speech_bytes = await convert(text_to_speech_bytes, ffmpeg_path=self._ffmpeg_path)
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
        await context.defer()

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

    def _get_language_code(self, language: str) -> Optional[str]:
        lang = self._get_language(language)
        if lang is not None:
            return lang['language']
        return None

    def _get_language_name(self, language_code: str) -> Optional[str]:
        return self._get_language(language_code)['name']

    def _get_language(self, language: str) -> Optional[Dict[str, str]]:
        for x in self._languages:
            if x['language'].lower() == language.lower() or x['name'].lower().split(' ')[0] == language.lower():
                return x
        return None

    def _get_voice_code(self, language: str) -> Optional[str]:
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
        for i, query in enumerate(queries):
            sub = language if i > 1 else language + '%'
            results = cursor.execute(query, (sub,))
            for result in results:
                connection.close()
                return result[0]

        connection.close()

        return None

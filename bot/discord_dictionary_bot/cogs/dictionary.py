import collections
import io
import asyncio
import logging
import sqlite3 as sql
import re
from typing import Union, Optional, Dict, List, Tuple, Set
from pathlib import Path
import html

from discord.ext.commands import Cog, Bot
from google.cloud import texttospeech
import babel
import discord
from discord import app_commands
from google.cloud.texttospeech_v1.services.text_to_speech.transports.grpc import TextToSpeechGrpcTransport
from google.cloud import translate_v2 as translate

from ..dictionary_api import DictionaryAPI, SequentialDictionaryAPI
from ..exceptions import InsufficientPermissionsException
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


def text_to_speech_pcm(text, language='en-us', gender=texttospeech.SsmlVoiceGender.SSML_VOICE_GENDER_UNSPECIFIED) -> bytes:
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


def is_valid_word(word: str):
    # Arbitrary maximum word size to hopefully prevent the bot from generating responses that are above Discord's message limit of 2000.
    if len(word) > 100:
        return False

    pattern = re.compile(r'^[a-zA-Z-\' ]+$')
    return pattern.search(word) is not None


class Dictionary(Cog):
    TRANSLATE_MAX_MESSAGE_LENGTH = 200

    # Languages to display in the `Translate` context menu. Discord enforces a limit of 25 items so these languages are a manually chosen subset of the supported languages
    TRANSLATE_CONTEXT_MENU_LANGUAGES = [{'language': 'ar', 'name': 'Arabic'}, {'language': 'zh', 'name': 'Chinese (Simplified)'}, {'language': 'da', 'name': 'Danish'}, {'language': 'nl', 'name': 'Dutch'},
                                        {'language': 'en', 'name': 'English'}, {'language': 'tl', 'name': 'Filipino'}, {'language': 'fi', 'name': 'Finnish'}, {'language': 'fr', 'name': 'French'}, {'language': 'de', 'name': 'German'},
                                        {'language': 'el', 'name': 'Greek'}, {'language': 'hi', 'name': 'Hindi'}, {'language': 'hu', 'name': 'Hungarian'}, {'language': 'id', 'name': 'Indonesian'}, {'language': 'it', 'name': 'Italian'},
                                        {'language': 'ja', 'name': 'Japanese'}, {'language': 'ko', 'name': 'Korean'}, {'language': 'pl', 'name': 'Polish'}, {'language': 'pt', 'name': 'Portuguese'}, {'language': 'ru', 'name': 'Russian'},
                                        {'language': 'es', 'name': 'Spanish'}, {'language': 'sv', 'name': 'Swedish'}, {'language': 'th', 'name': 'Thai'}, {'language': 'tr', 'name': 'Turkish'}, {'language': 'uk', 'name': 'Ukrainian'},
                                        {'language': 'vi', 'name': 'Vietnamese'}]

    def __init__(self, bot: Bot, dictionary_apis: [DictionaryAPI], ffmpeg_path: Union[str, Path]):
        super().__init__()

        self._bot = bot
        self._dictionary_apis = {api.id(): api for api in dictionary_apis}
        self._ffmpeg_path = Path(ffmpeg_path)

        # Create and populate a table of supported text-to-speech voices
        self._create_voices_table()

        # Each guild will have a lock to ensure that we only join 1 voice channel at a time
        self._guild_locks = collections.defaultdict(asyncio.Lock)

        # This dict keeps track of how many definition requests need the corresponding voice channel. This way we can leave the channel
        # only when we have finished all requests for that channel.
        self._voice_channels = collections.defaultdict(int)

        # Pending interaction IDs for anything that uses text-to-speech. This is used to cancel pending requests.
        self._pending_interactions: Set[int] = set()

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

        # Add context menus
        bot.tree.add_command(app_commands.ContextMenu(name='Translate', callback=self._translate_context_menu))

    async def _language_autocomplete(self, interaction: discord.Interaction, current: str) -> List[app_commands.Choice[str]]:
        supported_languages = self._languages
        matched_choices = [
            app_commands.Choice(name=language['name'], value=language['name'])
            for language in supported_languages if current.lower() in language['name'].lower()
        ]
        # Discord enforces a limit of 25 items that can be returned from an interaction, so just return the first 25
        return matched_choices[:25]

    async def _voice_autocomplete(self, interaction: discord.Interaction, current: str) -> List[app_commands.Choice[str]]:
        supported_voices = self._get_all_voices()
        matched_choices = []
        for voice in supported_voices:
            cl = current.lower()
            if voice[0] is not None and cl in voice[0].lower():
                matched_choices.append(app_commands.Choice(name=voice[0], value=voice[0]))
                continue
            if voice[1] is not None and cl in voice[1].lower():
                matched_choices.append(app_commands.Choice(name=voice[0], value=voice[0]))
                continue
            if voice[2] is not None and cl in voice[2].lower():
                matched_choices.append(app_commands.Choice(name=voice[0], value=voice[0]))
                continue
        # Discord enforces a limit of 25 items that can be returned from an interaction, so just return the first 25
        return matched_choices[:25]

    @app_commands.command(name='define', description='Gets the definition of a word.')
    @app_commands.describe(word='The word to define', text_to_speech='Use text to speech?', language='The language to translate the definition to.')
    @app_commands.autocomplete(language=_language_autocomplete)
    async def define(self, interaction: discord.Interaction, word: str, text_to_speech: bool = False, language: Optional[str] = None):

        # Get default language if none specified
        if language is None:
            language = self._bot._scoped_property_manager.get('language', interaction.channel)

        # Make sure this could be a word
        if not is_valid_word(word):
            await interaction.response.send_message('That\'s not a word.', ephemeral=True)
            return

        # Get voice channel the user is currently in (if any)
        voice_channel = interaction.user.voice.channel if isinstance(interaction.user, discord.Member) and interaction.user.voice is not None else None

        # Check for text-to-speech override
        text_to_speech_property = self._bot._scoped_property_manager.get('text_to_speech', interaction.channel)
        if text_to_speech_property == 'force' and voice_channel is not None:
            text_to_speech = True
        elif text_to_speech_property == 'disable':
            text_to_speech = False

        # Get voice code from language argument
        language_code = self._get_language_code(language)
        if language_code is None:
            await interaction.response.send_message(f'Could not find a language matching `{language}`!', ephemeral=True)
            return

        if text_to_speech:

            # Make sure that the user that requested this definition is in a voice channel if text-to-speech is enabled
            if text_to_speech and voice_channel is None:
                await interaction.response.send_message('You must be in a voice channel to use text-to-speech!', ephemeral=True)
                return

            # Check if this language has a supported voice
            if self._language_to_voice_map[language_code] is None:
                await interaction.response.send_message('I can\'t speak that language! Try again without using text-to-speech.', ephemeral=True)
                return

        # Defer our response since fetching the definition may take longer than a few seconds
        await interaction.response.defer()

        logger.info(f'Processing definition request: {{word: "{word}", text_to_speech: {text_to_speech}, language: "{language_code}"}}')

        # Get dictionary api
        dictionary_api_property = self._bot._scoped_property_manager.get('dictionary_apis', interaction.channel)
        dictionary_api = SequentialDictionaryAPI([self._dictionary_apis[api_id] for api_id in dictionary_api_property if api_id in self._dictionary_apis])

        # Translate the word to english
        if self._bot._scoped_property_manager.get('auto_translate', interaction.channel):
            word, detected_source_language = self._translate(word, 'en')
        else:
            detected_source_language = 'en'

        # Get definition
        definitions, definition_source = await dictionary_api.define_with_source(word)

        if len(definitions) == 0:
            reply = f'__**{word}**__'
            if detected_source_language != 'en':
                reply += f' (Translated from {self._get_language_name(detected_source_language)})'
            reply += '\nI couldn\'t find any definitions for that word.'
            await interaction.followup.send(reply)
            return

        # Record analytics only for valid words
        log_definition_request(word, text_to_speech, language, interaction.channel)

        # Translate word and definitions to target language
        if language_code != 'en':
            word, _ = self._translate(word, language_code)
            for i in range(len(definitions)):
                definitions[i]['word_type'], _ = self._translate(definitions[i]['word_type'], language_code)
                definitions[i]['definition'], _ = self._translate(definitions[i]['definition'], language_code)

        # Prepare response text and text-to-speech input
        show_definition_source = self._bot._scoped_property_manager.get('show_definition_source', interaction.channel)
        reply, text_to_speech_input = self.create_reply(word, definitions, definition_source=definition_source.name if show_definition_source else None, detected_source_language=detected_source_language)

        if text_to_speech:
            voice_code = self._language_to_voice_map[language_code]
            self._pending_interactions.add(interaction.id)
            try:
                await self._say(reply, interaction, voice_channel, voice_code, text_to_speech_input)
            except Exception as exception:
                logger.exception('Error saying things!', exc_info=exception)
            self._pending_interactions.discard(interaction.id)
        else:
            await interaction.followup.send(reply)

    @app_commands.command(name='say', description='Makes me say something.')
    @app_commands.describe(
        message='The message to say.',
        language='The language to translate the message to.',
        voice='The voice to use when speaking'
    )
    @app_commands.autocomplete(language=_language_autocomplete, voice=_voice_autocomplete)
    async def say(self, interaction: discord.Interaction, message: str, language: Optional[str] = None, voice: Optional[str] = None):

        # Limit message size
        if len(message) > 250:
            await interaction.response.send_message('Message is too long!', ephemeral=True)
            return

        # Get default language if none specified
        if language is None:
            language = self._bot._scoped_property_manager.get('language', interaction.channel)

        # Get voice channel the user is currently in (if any)
        voice_channel = interaction.user.voice.channel if isinstance(interaction.user, discord.Member) and interaction.user.voice is not None else None

        # Make sure that the user is in a voice channel
        if voice_channel is None:
            await interaction.response.send_message('You must be in a voice channel to use this command!', ephemeral=True)
            return

        # Get language code from language argument
        language_code = self._get_language_code(language)
        if language_code is None:
            await interaction.response.send_message(f'Could not find a language matching `{language}`!', ephemeral=True)
            return

        # Determine which voice to use
        if voice is None:
            # User didn't specify a voice, let's check if the language has a supported voice
            voice_code = self._language_to_voice_map[language_code]
            if voice_code is None:
                await interaction.response.send_message('I can\'t speak that language!', ephemeral=True)
                return
        else:
            voice_code = self._get_voice_code(voice)
            if voice_code is None:
                await interaction.response.send_message('I don\'t know that voice!', ephemeral=True)
                return

        # Defer response
        await interaction.response.defer()

        # Translate message to target language
        if language_code != 'en':
            message, detected_source_language = self._translate(message, language_code)

        # Replace @user and #channel with their display names
        text_to_speech_input = await self._replace_discord_tags(message)

        self._pending_interactions.add(interaction.id)
        try:
            await self._say(message, interaction, voice_channel, voice_code, text_to_speech_input, allow_partial_success=False)
        except Exception as exception:
            logger.exception('Error saying things!', exc_info=exception)
        self._pending_interactions.discard(interaction.id)

    async def _replace_discord_tags(self, text: str) -> str:
        # Replace tagged users
        pattern = r'<@(\d+)>'
        while True:
            match = re.search(pattern, text)
            if match is None:
                break
            item_id = int(match.group(1))
            user = await self._bot.fetch_user(item_id)
            if user is not None:
                text = re.sub(pattern, user.display_name, text, 1)
                continue

        # Replace tagged channels
        pattern = r'<#(\d+)>'
        while True:
            match = re.search(pattern, text)
            if match is None:
                break
            item_id = int(match.group(1))
            channel = await self._bot.fetch_channel(item_id)
            if channel is not None:
                text = re.sub(pattern, channel.name, text, 1)
                continue

        return text

    async def _say(self, text: str, interaction: discord.Interaction, voice_channel, language, text_to_speech_input=None, allow_partial_success=True):

        # Increment counter for this voice channel
        if voice_channel is not None:
            self._voice_channels[voice_channel] += 1

        # Get text-to-speech data
        text_to_speech_bytes = await self._get_text_to_speech(text_to_speech_input, language=language)

        # Check if we got valid text-to-speech data
        if text_to_speech_bytes.getbuffer().nbytes <= 0:

            logger.error('There was a problem generating the text-to-speech!')
            await interaction.followup.send('There was a problem generating the text-to-speech!')

            if allow_partial_success:
                # Send text chat reply
                await interaction.followup.send(text)

            # Update voice channel map
            self._voice_channels[voice_channel] -= 1

            # Disconnect from the voice channel if we don't need it anymore
            if self._voice_channels[voice_channel] <= 0:
                await self._leave_voice_channel(voice_channel)

        else:

            # Join the voice channel
            try:
                await self._guild_locks[interaction.guild].acquire()

                # Check if this request was cancelled
                if interaction.id not in self._pending_interactions:
                    await interaction.followup.send('Request cancelled!')

                    # Update voice channel map
                    self._voice_channels[voice_channel] -= 1

                    # Disconnect from the voice channel if we don't need it anymore
                    if self._voice_channels[voice_channel] <= 0:
                        await self._leave_voice_channel(voice_channel)
                    self._guild_locks[interaction.guild].release()

                    return

                voice_client = await self._join_voice_channel(voice_channel)
            except InsufficientPermissionsException as e:
                # Update voice channel map
                self._voice_channels[voice_channel] -= 1

                # Disconnect from the voice channel if we don't need it anymore
                if self._voice_channels[voice_channel] <= 0:
                    await self._leave_voice_channel(voice_channel)
                self._guild_locks[interaction.guild].release()
                await interaction.followup.send(f'I don\'t have permission to join your voice channel! Please grant me the following permissions: ' + ', '.join(f'`{x}`' for x in e.permissions) + '.')
                return

            # Send text chat reply
            await interaction.followup.send(text)

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

                    self._guild_locks[interaction.guild].release()

                asyncio.run_coroutine_threadsafe(after_coroutine(error), self._bot.loop)

            # Speak
            voice_client.play(discord.PCMAudio(text_to_speech_bytes), after=after)

    @app_commands.command(name='translate', description='Translate a message from one language to another.')
    @app_commands.describe(target_language='The language to translate to.', message='The message to translate.')
    @app_commands.autocomplete(target_language=_language_autocomplete)
    async def translate(self, interaction: discord.Interaction, target_language: str, message: str):

        # Limit message length
        if len(message) > Dictionary.TRANSLATE_MAX_MESSAGE_LENGTH:
            await interaction.response.send_message(f'Message is too long! Maximum length is {Dictionary.TRANSLATE_MAX_MESSAGE_LENGTH} characters.', ephemeral=True)
            return

        # Parse target language
        target_language_code = self._get_language_code(target_language)
        if target_language_code is None:
            await interaction.response.send_message(f'Invalid language!', ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)
        translated_message, detected_language = self._translate(message, target_language=target_language_code)
        await interaction.followup.send(self._create_translate_reply(message, detected_language, translated_message, target_language_code))

    def _translate(self, text: str, target_language: str, source_language: str = None):
        result = self._translate_client.translate(text, target_language=target_language, source_language=source_language)
        translated_text = html.unescape(result['translatedText'])

        if source_language is None:
            return translated_text, result['detectedSourceLanguage']
        else:
            return translated_text

    async def _translate_context_menu(self, interaction: discord.Interaction, message: discord.Message):
        view = discord.ui.View(timeout=None)
        selector = discord.ui.Select(placeholder='Select Language', options=[discord.SelectOption(label=language['name'], value=language['language']) for language in Dictionary.TRANSLATE_CONTEXT_MENU_LANGUAGES])

        async def callback(interaction: discord.Interaction):
            language = selector.values[0]
            content = discord.utils.remove_markdown(message.content)
            translated_message, detected_language = self._translate(content, target_language=language)
            source_language_name = self._get_language_name(detected_language)
            target_language_name = self._get_language_name(language)
            await interaction.response.edit_message(content=f'**__Original__** ({source_language_name})\n```\n{content}\n```**__Translated__** ({target_language_name})\n```\n{translated_message}\n```', view=None)

        selector.callback = callback
        view.add_item(selector)

        await interaction.response.send_message(view=view, ephemeral=True)

    def _create_translate_reply(self, message: str, source_language: str, translated_message: str, target_language: str):
        source_language_name = self._get_language_name(source_language)
        if source_language_name is None:
            source_language_name = source_language
            logger.warning('Could not find language name for code: ' + source_language)
        result = f'**__{source_language_name}__**\n'
        result += message + '\n'
        result += f'**__{self._get_language_name(target_language)}__**\n'
        result += translated_message
        return result

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

    def create_reply(self, word: str, definitions, definition_source: Optional[str] = None, detected_source_language: str = 'en') -> (str, str):
        """
        Create a reply.
        :param word:
        :param definitions:
        :param definition_source:
        :param detected_source_language:
        :return:
        """

        reply = f'__**{word}**__'
        if detected_source_language != 'en':
            reply += f' (Translated from {self._get_language_name(detected_source_language)})'
        reply += '\n'
        tts_input = f'{word}, '

        for i, definition in enumerate(definitions):
            word_type = definition['word_type']
            definition_text = definition['definition']

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

    @app_commands.command(name='stop', description='Makes the bot stop talking.')
    @app_commands.describe(clear_pending_requests='Clear all pending text-to-speech requests.')
    async def stop(self, interaction: discord.Interaction, clear_pending_requests: bool = False):
        # Get voice channel of current user
        voice_channel = interaction.user.voice.channel if isinstance(interaction.user, discord.Member) and interaction.user.voice is not None else None

        # Clear all pending requests
        if clear_pending_requests:
            self._pending_interactions.clear()

        # Get voice client
        for voice_client in self._bot.voice_clients:
            if voice_client.channel == voice_channel:
                voice_client.stop()
                await interaction.response.send_message('Okay, I\'ll be quiet.')
                return

        await interaction.response.send_message('I\'m not even talking!', ephemeral=True)

    @staticmethod
    def _language_code_to_language_name(language_code: str) -> Optional[str]:
        try:
            return babel.Locale.parse(language_code, sep='-').get_display_name('en')
        except babel.core.UnknownLocaleError:
            pass
        try:
            return babel.Locale.parse(language_code.split('-')[0]).get_display_name('en')
        except babel.core.UnknownLocaleError:
            pass
        return None

    @staticmethod
    def _create_voices_table():
        # Connect to database
        connection = sql.connect('database.db')
        cursor = connection.cursor()

        # Create table
        cursor.execute('CREATE TABLE IF NOT EXISTS voices (voice_code text UNIQUE, language_code text, language_name text, voice_type text, voice_gender text)')

        # Add supported voices
        client = texttospeech.TextToSpeechClient()
        response = client.list_voices()
        for voice in response.voices:
            voice_code = voice.name
            voice_gender = voice.ssml_gender.name
            language_code = '-'.join(voice_code.split('-')[:2])
            language_name = Dictionary._language_code_to_language_name(language_code)
            voice_type = voice_code.split('-')[2]
            cursor.execute(f'INSERT OR IGNORE INTO voices VALUES (?, ?, ?, ?, ?)', (voice_code, language_code, language_name, voice_type, voice_gender))

        connection.commit()
        connection.close()

    def _get_language_code(self, language: str) -> Optional[str]:
        lang = self._get_language(language)
        if lang is not None:
            return lang['language']
        return None

    def _get_language_name(self, language_code: str) -> Optional[str]:
        language = self._get_language(language_code)
        if language is None:
            return None
        return language['name']

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
        q = 'ORDER BY CASE voice_type WHEN "Wavenet" THEN 0 ELSE 1 END, CASE voice_gender WHEN "FEMALE" THEN 0 ELSE 1 END ASC'
        queries = (
            f'SELECT * FROM voices WHERE voice_code LIKE ? {q}',
            f'SELECT * FROM voices WHERE language_code LIKE ? {q}',
            f'SELECT * FROM voices WHERE language_name LIKE ? {q}',
            # f'SELECT * FROM voices WHERE language_region LIKE ? {q}'
        )

        # Return first value that matches a query
        for i, query in enumerate(queries):
            sub = language if i > 1 else language + '%'
            results = cursor.execute(query, (sub,))
            for result in results:
                connection.close()
                return result[0]

        # Disconnect from database
        connection.close()

        return None

    def _get_all_voices(self) -> List[Tuple[str, str, str]]:
        # Connect to database
        connection = sql.connect('database.db')
        cursor = connection.cursor()

        # Get all voices
        voices = []
        results = cursor.execute('SELECT voice_code, language_code, language_name FROM voices')
        for result in results:
            voices.append(result)

        # Disconnect from database
        connection.close()

        return voices

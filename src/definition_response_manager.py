import asyncio
import collections
import threading
import io
import time
from concurrent.futures.thread import ThreadPoolExecutor
from exceptions import InsufficientPermissionsException
from dictionary_api import DictionaryAPI
from m_logging import log
import discord
import pathlib
import utils
from google.cloud import texttospeech
from google.cloud.texttospeech_v1.services.text_to_speech.transports.grpc import TextToSpeechGrpcTransport
import subprocess
from discord_bot_client import DiscordBotClient


def text_to_speech_pcm(text, language='en-us', gender=texttospeech.SsmlVoiceGender.NEUTRAL):
    # Create a text-to-speech client with maximum receive size of 24MB
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
    try:
        response = client.synthesize_speech(input=synthesis_input, voice=voice, audio_config=audio_config)
        return response.audio_content
    except Exception as e:
        log(f'Failed to generate text-to-speech data: {e}. You might be using an invalid language: {language_code}', 'error')
        return b''


def create_reply(word, definitions, reverse=False):
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


class DefinitionRequest:

    def __init__(self, user: discord.User, word, message: discord.Message, reverse=False, text_to_speech=False, language='en-us'):
        self.user = user
        self.voice_channel = user.voice.channel if isinstance(user, discord.Member) and user.voice is not None else None
        self.word = word
        self.message = message
        self.reverse = reverse
        self.text_to_speech = text_to_speech
        self.language = language

    def __repr__(self):
        return f'{{W: "{self.word}", M: "{self.message.content}", R: "{self.reverse}", TTS: "{self.text_to_speech}", L: "{self.language}"}}'


class DefinitionResponseManager:
    """
    This class is responsible for scheduling and executing definition requests. This class maintains a separate queue for each 'discord.TextChannel' and incoming definition requests get added to the appropriate queue. If a definition
    request requires the use of a 'discord.VoiceChannel', all other definition requests that also require that same voice channel must wait.
    """

    def __init__(self, client: DiscordBotClient, ffmpeg_path: pathlib.Path, api: DictionaryAPI):
        self._client = client
        self._ffmpeg_path = ffmpeg_path
        self._api = api

        # Each text channel will have its own request queue to allow simultaneous responses across channels
        self._request_queues = {}
        self._request_queues_lock = threading.Lock()

        # Keep track of which voice channels we need to respond to. This way we can leave the channel only when we have finished all requests for that channel
        self._voice_channels = collections.defaultdict(int)
        self._voice_channels_map_lock = threading.Lock()

        # This dictionary will store a 'threading.Lock' for each voice channel that should be held by a 'MessageQueue' when it is using the corresponding voice channel.
        self._voice_channels_locks = collections.defaultdict(threading.Lock)

    @property
    def client(self):
        return self._client

    @property
    def api(self):
        return self._api

    @property
    def voice_channels(self):
        """
        This should only be used by 'MessageQueue'.
        :return: A dictionary of voice channels.
        """
        return self._voice_channels

    @property
    def voice_channel_map_lock(self):
        """
        This should only be used by 'MessageQueue'.
        :return: A 'threading.Lock' used to synchronize the map of voice channels.
        """
        return self._voice_channels_map_lock

    @property
    def voice_channels_locks(self):
        return self._voice_channels_locks

    def add(self, definition_request: DefinitionRequest) -> None:
        """
        Add a definition request.
        :param definition_request: The definition request to add.
        """
        message = definition_request.message
        text_channel = message.channel

        # Add request to queue
        with self._request_queues_lock:
            if text_channel not in self._request_queues:
                self._request_queues[text_channel] = MessageQueue(self, text_channel, self._ffmpeg_path)
            self._request_queues[text_channel].add(definition_request)

        # Check if this request needs to use a voice channel
        if definition_request.text_to_speech:
            voice_channel = definition_request.voice_channel
            if voice_channel is not None:
                self._voice_channels_map_lock.acquire()
                self._voice_channels[voice_channel] += 1
                self._voice_channels_map_lock.release()

    def stop(self, text_channel: discord.TextChannel):
        """
        Clear all requests for the specified text channel and stops any in-progress requests for that channel.
        :param text_channel:
        """
        with self._request_queues_lock:
            if text_channel not in self._request_queues:
                self._client.sync(utils.send_split('Okay, i\'ll be quiet.', text_channel))
                return

            self._request_queues[text_channel].stop()

    def next(self, text_channel: discord.TextChannel) -> None:
        """
        If the bot is currently reading out a definition, this will make it skip to the next one.
        :param text_channel: The 'discord.TextChannel' the command was sent in.
        """
        with self._request_queues_lock:
            if text_channel not in self._request_queues:
                self._client.sync(utils.send_split('Nothing in queue.', text_channel))
                return  # nothing in queue

            self._request_queues[text_channel].next()


class MessageQueue:
    """
    This class represents a single definition request queue and is responsible for processing requests on a single 'discord.TextChannel'. These are created by the DefinitionResponseManager.
    """

    def __init__(self, definition_response_manager: DefinitionResponseManager, text_channel: discord.TextChannel, ffmpeg_path):
        self._ffmpeg_path = ffmpeg_path
        self._definition_response_manager = definition_response_manager
        self._text_channel: discord.abc.Messageable = text_channel
        self._client = definition_response_manager.client

        # This queue stores incoming 'DefinitionRequest's. The condition is notified whenever a new item is added to the queue.
        self._queue = collections.deque()
        self._queue_lock = threading.Lock()
        self._queue_condition = threading.Condition(self._queue_lock)

        # The current voice client we are using for text-to-speech
        self._voice_client: discord.VoiceClient = None
        self._voice_client_lock = threading.Lock()

        # This lock ensures that only 1 queue item is processed at a time. This is needed because the async function '_process_definition_request' may return before we are finished with the voice channel so we need to wait until
        # text-to-speech has finished before processing the next item in the queue
        self._process_lock = threading.Lock()

        # Used for properly handling 'stop()' requests.
        self._stop_lock = threading.Lock()

        # This dictionary stores 'concurrent.future.Future's for definition requests. These are added immediately when a new request comes in so that multiple requests can be processed asynchronously before we are ready to display the
        # results. This provides a significant speed improvement when there are multiple definition requests in the queue.
        self._request_futures = {}
        self._request_futures_lock = threading.Lock()
        self._request_thread_pool = ThreadPoolExecutor()

        # Start processing queue
        threading.Thread(target=self.run).start()

    def _get_definition_and_text_to_speech(self, definition_request: DefinitionRequest) -> (str, io.BytesIO):
        """
        Gets the definitions for the specified word and also creates the text channel reply and generates the corresponding text-to-speech data.
        :param definition_request: A 'DefinitionRequest'.
        :return: Normally returns a tuple(str, io.BytesIO) containing the textual response and text-to-speech response. If there is an error, this will return a tuple(None, None). If text-to-speech is disabled, it will return a
        tuple(str, None).
        """

        # Get definitions
        definitions = self._definition_response_manager.api.define(definition_request.word)
        if len(definitions) == 0:
            return None, None

        # Create text channel reply and text-to-speech input
        reply, tts_input = create_reply(definition_request.word, definitions, definition_request.reverse)

        # Get text-to-speech data
        if definition_request.text_to_speech:
            buffer = self._get_text_to_speech(tts_input, definition_request.language)
            return reply, buffer

        return reply, None

    def add(self, definition_request: DefinitionRequest) -> None:
        """
        Add a definition request to the end of the queue.
        :param definition_request: The definition request to add.
        """

        # Make sure the user is in a voice channel if text-to-speech is enabled
        if definition_request.text_to_speech:
            if definition_request.voice_channel is None:
                self._client.sync(utils.send_split('You must be in a voice channel to use the text-to-speech flag!', definition_request.message.channel))
                return

        # Add request to thread pool
        with self._request_futures_lock:
            self._request_futures[definition_request] = self._request_thread_pool.submit(self._get_definition_and_text_to_speech, definition_request)

        # Add request to queue
        with self._queue_lock:
            self._queue.append(definition_request)
            self._queue_condition.notify()

    def run(self) -> None:
        """
        Starts processing this message queue.
        """
        while True:

            # Acquire the lock to ensure only 1 item is processed at a time
            self._process_lock.acquire()

            # Wait for an item to enter the queue
            with self._queue_lock:
                while len(self._queue) == 0:
                    log(f'[{self}] Waiting for more requests')
                    self._queue_condition.wait()
                log(f'[{self}] Processing {len(self._queue)} items')

                # Get definition request
                definition_request = self._queue.popleft()

            self._stop_lock.acquire()

            # Process the definition request
            self._process_definition_request(definition_request)

    def _get_text_to_speech(self, tts_input: str, language: str) -> io.BytesIO:
        result = io.BytesIO()

        text_to_speech_bytes = text_to_speech_pcm(tts_input, language=language)
        if len(text_to_speech_bytes) == 0:
            return result

        # Convert to proper format
        text_to_speech_bytes = convert(text_to_speech_bytes, ffmpeg_path=self._ffmpeg_path)
        result.write(text_to_speech_bytes)
        result.seek(0)

        return result

    def _say(self, text: str, voice_channel=None, language='en-us', tts_input=None, after_callback=None):

        # Send voice channel reply
        if voice_channel is not None:

            # Generate text to speech data
            buffer = self._get_text_to_speech(tts_input, language)

            # Join voice channel
            try:
                voice_client = self._client.sync(self._client.join_voice_channel(voice_channel)).result()
            except InsufficientPermissionsException as e:

                self._client.sync(utils.send_split(f'I don\'t have permission to join your voice channel! Please grant me the following permissions: ' + ', '.join(f'`{x}`' for x in e.permissions) + '.', self._text_channel))

                # Call pass-through callback
                after_callback(None)
                return

            except Exception as e:
                log(f'{self} Failed to connect to the voice channel: {e}', 'error')
                self._client.sync(utils.send_split(f'I could not connect to the voice channel!', self._text_channel))

                # Call pass-through callback
                after_callback(None)
                return

            # Acquire lock for this voice channel
            self._definition_response_manager.voice_channels_locks[voice_channel].acquire()

            with self._voice_client_lock:
                self._voice_client = voice_client

            # Send text chat reply
            self._client.sync(utils.send_split(text, self._text_channel))

            # Create callback for when we are done speaking
            def after(error):

                if error is not None:
                    log(f'Exception occurred while playing audio: {error}', 'error')

                # Release voice channel lock
                with self._voice_client_lock:
                    self._voice_client = None
                self._definition_response_manager.voice_channels_locks[voice_channel].release()

                # Call pass-through callback
                if after_callback is not None:
                    after_callback(error)

            # Speak
            voice_client.play(discord.PCMAudio(buffer), after=after)

        else:

            # Send text chat reply
            self._client.sync(utils.send_split(text, self._text_channel))

            # Call pass-through callback
            after_callback(None)

    def _process_definition_request(self, definition_request: DefinitionRequest) -> None:
        """
        Process a definition request. This will fetch the definition from the dictionary API, fetch the text-to-speech data from the text-to-speech API, and post the definition to the text channel and voice channel.
        :param definition_request: The definition request to process.
        """
        word = definition_request.word
        message = definition_request.message
        text_to_speech = definition_request.text_to_speech
        voice_channel = definition_request.voice_channel

        log(f'[{self}] Processing request: {definition_request}')

        # Get result from request future
        with self._request_futures_lock:
            reply, buffer = self._request_futures[definition_request].result()
            self._request_futures.pop(definition_request)

        if reply is None:

            # Create callback for when we are done speaking
            def after(error):

                if error is not None:
                    log(f'Exception occurred while playing audio: {error}', 'error')

                if text_to_speech and voice_channel is not None:

                    # Update voice channel map
                    with self._definition_response_manager.voice_channel_map_lock:
                        self._definition_response_manager.voice_channels[voice_channel] -= 1

                    # Disconnect from the voice channel if we don't need it anymore
                    if self._definition_response_manager.voice_channels[voice_channel] == 0:
                        self._client.sync(self._client.leave_voice_channel(voice_channel))

                # Release process lock
                self._process_lock.release()

            # Send response
            self._say(f'__**{word}**__\nThere was a problem finding that word.', voice_channel=None if not text_to_speech else voice_channel, language=definition_request.language, tts_input=f'{word}. There was a problem finding that word.',
                      after_callback=after)

            # Release stop lock
            self._stop_lock.release()

            return

        if text_to_speech and voice_channel is not None:

            # If we need the voice channel, send both the text and audio response at the same time
            if buffer is not None:

                # Join the voice channel
                try:
                    voice_client = self._client.sync(self._client.join_voice_channel(voice_channel)).result()
                except InsufficientPermissionsException as e:

                    self._client.sync(utils.send_split(f'I don\'t have permission to join your voice channel! Please grant me the following permissions: ' + ', '.join(f'`{x}`' for x in e.permissions) + '.', self._text_channel))

                    # Release stop lock
                    self._stop_lock.release()

                    # Release process lock
                    self._process_lock.release()

                    return

                except Exception as e:
                    log(f'{self} Failed to connect to voice channel: {e}', 'error')
                    self._client.sync(utils.send_split(f'I could not connect to the voice channel!', self._text_channel))

                    # Release stop lock
                    self._stop_lock.release()

                    # Release process lock
                    self._process_lock.release()

                    return

                # Acquire lock for this voice channel
                self._definition_response_manager.voice_channels_locks[voice_channel].acquire()

                with self._voice_client_lock:
                    self._voice_client = voice_client

                # Temporary fix for (https://github.com/TychoTheTaco/Discord-Dictionary-Bot/issues/1)
                time.sleep(3)

                # Send text chat reply
                self._client.sync(utils.send_split(reply, message.channel))

                # Speak
                def after(error):

                    if error is not None:
                        log(f'Exception occurred while playing audio: {error}', 'error')

                    with self._voice_client_lock:
                        self._voice_client = None

                    self._definition_response_manager.voice_channels_locks[voice_channel].release()

                    # Update voice channel map
                    with self._definition_response_manager.voice_channel_map_lock:
                        self._definition_response_manager.voice_channels[voice_channel] -= 1

                    # Disconnect from the voice channel if we don't need it anymore
                    if self._definition_response_manager.voice_channels[voice_channel] == 0:
                        asyncio.run_coroutine_threadsafe(self._client.leave_voice_channel(voice_channel), self._client.loop)

                    # Release process lock
                    self._process_lock.release()

                voice_client.play(discord.PCMAudio(buffer), after=after)

                # Release stop lock
                self._stop_lock.release()

            else:

                # Release stop lock
                self._stop_lock.release()

                self._client.sync(utils.send_split('There was a problem processing the text-to-speech.', message.channel))

        else:

            # Release stop lock
            self._stop_lock.release()

            # Send text chat reply
            self._client.sync(utils.send_split(reply, message.channel))

            # Release process lock
            self._process_lock.release()

    def _clear(self) -> None:
        """
        Clear the queue and update voice channel map.
        """
        with self._queue_lock, self._definition_response_manager.voice_channel_map_lock:
            for item in self._queue:
                if item.voice_channel:
                    self._definition_response_manager.voice_channels[item.voice_channel] -= 1
            self._queue.clear()
            self._queue_condition.notify()

    def stop(self) -> None:
        """
        Clears the queue and immediately stops processing definition requests.
        """
        with self._stop_lock:
            self._clear()

            # Stop using the voice channel
            with self._voice_client_lock:
                if self._voice_client:
                    self._voice_client.stop()

        # Send text channel reply
        self._client.sync(utils.send_split('Okay, i\'ll be quiet.', self._text_channel))

    def next(self) -> None:
        """
        If we are currently reading out a definition, skips to the next definition request. This will have no effect if we are not currently using a voice channel.
        """
        with self._stop_lock:
            # Stop using the voice channel
            with self._voice_client_lock:
                if self._voice_client:
                    self._voice_client.stop()

        # Send text channel reply
        self._client.sync(utils.send_split('Skipped to next word.', self._text_channel))

    def __repr__(self):
        if isinstance(self._text_channel, discord.TextChannel):
            return f'MessageQueue {{G: "{self._text_channel.guild}", C: "{self._text_channel.name}"}}'
        elif isinstance(self._text_channel, discord.DMChannel):
            return f'MessageQueue {{DM with {self._text_channel.recipient.name}}}'
        return f'MessageQueue {{{self._text_channel}}}'


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

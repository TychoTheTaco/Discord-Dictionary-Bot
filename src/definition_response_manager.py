import asyncio
import collections
import threading
import io

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
        print('Failed to get text to speech data:', e)
        return None


class DefinitionRequest:

    def __init__(self, user: discord.Member, word, message, reverse=False, text_to_speech=False, language='en-us'):
        self.user = user
        self.voice_state = user.voice
        self.word = word
        self.message = message
        self.reverse = reverse
        self.text_to_speech = text_to_speech
        self.language = language


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
            voice_channel = None if definition_request.voice_state is None else definition_request.voice_state.channel
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
        self._text_channel = text_channel
        self._client = definition_response_manager._client

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

        self._stop_lock = threading.Lock()

        # Start processing queue
        threading.Thread(target=self.run).start()

    def add(self, definition_request: DefinitionRequest) -> None:
        """
        Add a definition request to the end of the queue.
        :param definition_request: The definition request to add.
        """
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
                    log(f'[{self}] Waiting for more requests...')
                    self._queue_condition.wait()
                log(f'[{self}] Processing {len(self._queue)} items...')

                # Get definition request
                definition_request = self._queue.popleft()

            self._stop_lock.acquire()

            # Process the definition request
            self._process_definition_request(definition_request)

    def _say(self, text: str, voice_channel=None, language='en-us', tts_input=None, after_callback=None):

        # Send voice channel reply
        if voice_channel is not None:

            # Generate text to speech data
            text_to_speech_bytes = text_to_speech_pcm(tts_input, language=language)

            # Join voice channel
            voice_client = self._client.sync(self._client.join_voice_channel(voice_channel)).result()

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

            # Write text-to-speech data to a BytesIO file
            file = io.BytesIO()
            file.write(text_to_speech_bytes)

            # Speak
            voice_client.play(BytesIOPCMAudio(file, executable=str(self._ffmpeg_path)), after=after)

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
        reverse = definition_request.reverse
        text_to_speech = definition_request.text_to_speech
        language = definition_request.language

        voice_channel = None if definition_request.voice_state is None else definition_request.voice_state.channel

        # Get definitions
        definitions = self._definition_response_manager.api.define(word)
        if len(definitions) == 0:

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
            self._say(f'__**{word}**__\nThere was a problem finding that word.', voice_channel=None if not text_to_speech else voice_channel, language=language, tts_input=f'{word}. There was a problem finding that word.', after_callback=after)

            # Release stop lock
            self._stop_lock.release()

            return

        # Create text channel reply
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

        if text_to_speech and voice_channel is not None:

            # Generate text-to-speech data
            text_to_speech_bytes = text_to_speech_pcm(tts_input, language=language) if voice_channel is not None else b''
            file = io.BytesIO()
            file.write(text_to_speech_bytes)

            # If we need the voice channel, send both the text and audio response at the same time
            if len(text_to_speech_bytes) > 0:

                # Join the voice channel
                voice_client = self._client.sync(self._client.join_voice_channel(voice_channel)).result()

                # Acquire lock for this voice channel
                self._definition_response_manager.voice_channels_locks[voice_channel].acquire()

                with self._voice_client_lock:
                    self._voice_client = voice_client

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

                voice_client.play(BytesIOPCMAudio(file, executable=str(self._ffmpeg_path)), after=after)

                # Release stop lock
                self._stop_lock.release()

            else:
                log('Failed to generate text-to-speech data', 'error')

                # Release stop lock
                self._stop_lock.release()

                self._client.sync(utils.send_split('**There was a problem processing the text-to-speech.**', message.channel))

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
                if item.voice_state:
                    self._definition_response_manager.voice_channels[item.voice_state.channel] -= 1
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
        return f'MessageQueue {{G: "{self._text_channel.guild}", C: "{self._text_channel.name}"}}'


class BytesIOPCMAudio(discord.PCMAudio):

    def __init__(self, source, executable='ffmpeg'):
        self._source = source

        # Start ffmpeg process
        self._process = subprocess.Popen(
            [executable, '-y', '-i', 'pipe:0', '-ac', '2', '-f', 's16le', 'pipe:1', '-loglevel', 'panic'],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE
        )

        # Start writing data to process stdin
        threading.Thread(target=self.sp).start()

        super().__init__(self._process.stdout)

    def sp(self):
        self._process.stdin.write(self._source.getvalue())
        self._process.stdin.close()


def split(message, split_size):
    messages = []
    while len(message) > 0:

        # Find closest space before 'split_size' limit
        if len(message) > split_size:
            space_index = split_size
            while message[space_index] != ' ':
                space_index -= 1
        else:
            space_index = len(message)

        # Add chunk to message list
        m = message[:space_index]
        messages.append(m)

        # Remove chunk from message
        message = message[space_index:]

    return messages
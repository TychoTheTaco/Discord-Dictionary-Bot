import asyncio
import collections
import threading
import time
import io
import discord
import pathlib
import requests
import utils
from google.cloud import texttospeech
from google.cloud.texttospeech_v1.services.text_to_speech.transports.grpc import TextToSpeechGrpcTransport
import subprocess
from discord_bot_client import DiscordBotClient


def get_definition(word):
    return requests.get('https://owlbot.info/api/v2/dictionary/' + word.replace(' ', '%20') + '?format=json')


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

    def __init__(self, client: DiscordBotClient, ffmpeg_path: pathlib.Path):
        self._client = client
        self._ffmpeg_path = ffmpeg_path

        # Each text channel will have its own request queue to allow simultaneous responses across channels
        self._request_queues = {}

        # Keep track of which voice channels we need to respond to. This way we can leave the channel only when we have finished all requests for that channel
        self._voice_channels = collections.defaultdict(int)
        self._voice_channels_map_lock = threading.Lock()

        # This dictionary will store a 'threading.Lock' for each voice channel that should be held by a 'MessageQueue' when it is using the corresponding voice channel.
        self._voice_channels_locks = collections.defaultdict(threading.Lock)

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
        if text_channel not in self._request_queues:
            self._request_queues[text_channel] = MessageQueue(self, self._ffmpeg_path)
        self._request_queues[text_channel].add(definition_request)

        # Check if this request needs to use a voice channel
        if definition_request.text_to_speech:
            voice_channel = None if definition_request.voice_state is None else definition_request.voice_state.channel
            if voice_channel is not None:
                self._voice_channels_map_lock.acquire()
                self._voice_channels[voice_channel] += 1
                self._voice_channels_map_lock.release()

    async def clear(self, text_channel: discord.TextChannel):
        """
        Clear all requests for the specified text channel.
        :param text_channel:
        """
        print(f'[{id(self._lock)}]: 84 Wait...')
        self._lock.acquire()
        print(f'[{id(self._lock)}]: 84 Acquired')
        for item in self._request_queues[text_channel]._queue:

            # Remove voice channel requirement for this request
            voice_state = item.message.author.voice
            voice_channel = None if voice_state is None else voice_state.channel
            if not item.text_to_speech:
                voice_channel = None
            if voice_channel is not None:
                self._voice_channels[voice_channel] -= 1

                # Leave voice channels with no items in the queue
                print(self._voice_channels[voice_channel])
                if self._voice_channels[voice_channel] == 0:
                    await self._client.leave_voice_channel(voice_channel)

        # Stop any current voice activity and clear the request queue
        await self._request_queues[text_channel].stop()

        self._lock.release()
        print(f'[{id(self._lock)}]: 84 Released')

        await text_channel.send('Ok, i\'ll be quiet.')

    def next(self, message):
        voice_state = message.author.voice
        voice_channel = voice_state.channel if voice_state is not None else None

        # Check if user is in a voice channel
        if voice_channel is None:
            self._client.sync(utils.send_split('You must be in a voice channel to use that command.', message.channel))
            return

        # Find the message queue that is using the voice channel
        for message_queue in self._request_queues.values():
            if message_queue._voice_channel == voice_channel:
                message_queue.next()
                return

        #
        self._client.sync(utils.send_split(f'There are no more words in the queue.', message.channel))


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


class MessageQueue:
    """
    This class represents a single definition request queue and is responsible for processing requests on a single 'discord.TextChannel'. These are created by the DefinitionResponseManager.
    """

    def __init__(self, definition_response_manager: DefinitionResponseManager, ffmpeg_path):
        self._ffmpeg_path = ffmpeg_path
        self._definition_response_manager = definition_response_manager
        self._client = definition_response_manager._client
        self._queue = collections.deque()
        self._queue_lock = threading.Lock()
        self._condition = threading.Condition(self._queue_lock)
        threading.Thread(target=self.run).start()

        # The current voice client we are using for text-to-speech
        self._voice_client: discord.VoiceClient = None
        self._voice_client_lock = threading.Lock()

    def add(self, definition_request: DefinitionRequest) -> None:
        """
        Add a definition request to the end of the queue.
        :param definition_request: The definition request to add.
        """
        with self._queue_lock:
            self._queue.append(definition_request)
            self._condition.notify()

    def run(self) -> None:
        """
        Starts processing this message queue.
        """
        while True:

            # Wait for an item to enter the queue
            with self._queue_lock:
                if len(self._queue) == 0:
                    self._condition.wait()

            print(f'[MessageQueue {id(self)}] Processing {len(self._queue)} items...')

            # Process all items currently in the queue
            while len(self._queue) > 0:

                # Get definition request
                definition_request = self._queue.popleft()

                # Process the definition request
                asyncio.run_coroutine_threadsafe(self._process_definition_request(definition_request), self._client.loop).result()

                # Check if the request needed to use a voice channel
                if definition_request.text_to_speech:
                    voice_state = definition_request.voice_state
                    voice_channel = None if voice_state is None else voice_state.channel

                    with self._definition_response_manager.voice_channel_map_lock:
                        self._definition_response_manager.voice_channels[voice_channel] -= 1

                    # Disconnect from the voice channel if we don't need it anymore
                    if self._definition_response_manager.voice_channels[voice_channel] == 0:
                        asyncio.run_coroutine_threadsafe(self._client.leave_voice_channel(voice_channel), self._client.loop)

            print(f'[MessageQueue {id(self)}] Finished queue')

    async def _say(self, text: str, text_channel: discord.TextChannel, voice_channel=None, language='en-us', tts_input=None):

        # Generate text to speech
        text_to_speech_bytes = text_to_speech_pcm(tts_input, language=language) if voice_channel is not None else None

        # Send voice channel reply
        if voice_channel is not None:

            # Join voice channel
            voice_client = await self._client.join_voice_channel(voice_channel)

            # Acquire lock for this voice channel
            self._definition_response_manager.voice_channels_locks[voice_channel].acquire()

            with self._voice_client_lock:
                self._voice_client = voice_client

            # Send text chat reply
            await utils.send_split(text, text_channel)

            # Speak
            def after():
                with self._voice_client_lock:
                    self._voice_client = None
                self._definition_response_manager.voice_channels_locks[voice_channel].release()
            file = io.BytesIO()
            file.write(text_to_speech_bytes)
            voice_client.play(BytesIOPCMAudio(file, executable=str(self._ffmpeg_path)))

        else:
            # Send text chat reply
            await utils.send_split(text, text_channel)

        self._voice_channel = None

    async def _process_definition_request(self, definition_request: DefinitionRequest) -> None:
        """
        Process a definition request. This will fetch the definition from the dictionary API, fetch the text-to-speech data from the text-to-speech API, and post the definition to the text channel and voice channel.
        :param definition_request: The definition request to process.
        """
        word = definition_request.word
        message = definition_request.message
        reverse = definition_request.reverse
        text_to_speech = definition_request.text_to_speech
        language = definition_request.language

        if text_to_speech:
            voice_state = message.author.voice
            voice_channel = None if voice_state is None else voice_state.channel
        else:
            voice_channel = None

        # Get definitions
        response = get_definition(word)
        if response.status_code != 200:
            await self._say(f'__**{word}**__\nI don\'t know that word.', message.channel, voice_channel=voice_channel, language=language, tts_input=f'{word}. I don\'t know that word.')
            return

        try:
            definitions = response.json()
        except ValueError:  # Catch a ValueError here because sometimes requests uses simplejson instead of json as a backend
            await utils.send_split(f'__**{word}**__\nThere was a problem finding word.', message.channel)
            return

        # Create text channel reply
        if reverse:
            word = word[::-1]
        reply = f'__**{word}**__\n'
        tts_input = f'{word}, '
        for i, definition in enumerate(definitions):
            word_type = definition['type']
            definition_text = definition['definition']

            if reverse:
                word_type = word_type[::-1]
                definition_text = definition_text[::-1]

            reply += f'**[{i + 1}]** ({word_type})\n' + definition_text + '\n'
            tts_input += f' {i + 1}, {word_type}, {definition_text}'

        # Generate text-to-speech
        if text_to_speech:
            voice_state = message.author.voice
            voice_channel = None if voice_state is None else voice_state.channel
        else:
            voice_channel = None

        # Generate text-to-speech data
        text_to_speech_bytes = text_to_speech_pcm(tts_input, language=language) if voice_channel is not None else None
        file = io.BytesIO()
        file.write(text_to_speech_bytes)

        # If we need the voice channel, send both the text and audio response at the same time
        if voice_channel is not None:
            if text_to_speech_bytes is not None:

                # Join the voice channel
                voice_client = await self._client.join_voice_channel(voice_channel)

                # Acquire lock for this voice channel
                self._definition_response_manager.voice_channels_locks[voice_channel].acquire()

                with self._voice_client_lock:
                    self._voice_client = voice_client

                # Send text chat reply
                await utils.send_split(reply, message.channel)

                # Speak
                def after():
                    with self._voice_client_lock:
                        self._voice_client = None
                    self._definition_response_manager.voice_channels_locks[voice_channel].release()
                voice_client.play(BytesIOPCMAudio(file, executable=str(self._ffmpeg_path)), after=after)

            else:
                await utils.send_split('**There was a problem processing the text-to-speech.**', message.channel)

        else:
            # Send text chat reply
            await utils.send_split(reply, message.channel)

    def stop(self) -> None:
        """
        Clears the queue and immediately stops processing definition requests.
        """
        # Clear the queue and update voice channel map
        with self._queue_lock, self._definition_response_manager.voice_channel_map_lock:
            for item in self._queue:
                if item.voice_channel:
                    self._definition_response_manager.voice_channels[item.voice_channel] -= 1
            self._queue.clear()

        # Stop using the voice channel
        with self._voice_client_lock:
            if self._voice_client:
                self._voice_client.stop()

    def next(self) -> None:
        """
        Skips to the next definition request.
        """
        with self._voice_client_lock:
            if self._voice_client:
                self._voice_client.stop()


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
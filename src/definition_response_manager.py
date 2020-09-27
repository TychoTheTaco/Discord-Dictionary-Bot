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
import subprocess


def get_definition(word):
    return requests.get('https://owlbot.info/api/v2/dictionary/' + word.replace(' ', '%20') + '?format=json')


class DefinitionResponseManager:

    def __init__(self, client: discord.Client, ffmpeg_path: pathlib.Path):
        """
        This class is responsible for managing definition requests. It decides which queue to add the request to and it keeps track of which voice channels need to remain connected.
        """
        self._client = client
        self._ffmpeg_path = ffmpeg_path

        # Each text channel will have its own request queue to allow simultaneous responses across channels
        self._request_queues = {}

        # Keep track of which voice channels we need to respond to. This way we can leave the channel only when we have finished all requests for that channel
        self._voice_channels = collections.defaultdict(int)

        # Lock used to synchronize 'self._voice_channels'
        self._lock = threading.Lock()

    def add(self, word, message: discord.Message, reverse=False, text_to_speech=False):
        """
        Add a request
        :param word:
        :param message:
        :param reverse:
        :param text_to_speech:
        :return:
        """
        text_channel = message.channel

        # Add request to queue
        if text_channel not in self._request_queues:
            self._request_queues[text_channel] = MessageQueue(self._client, self._ffmpeg_path)
        self._request_queues[text_channel].add(word, message, reverse=reverse, text_to_speech=text_to_speech)

        # Add voice channel
        if text_to_speech:
            voice_state = message.author.voice
            voice_channel = None if voice_state is None else voice_state.channel
            if voice_channel is not None:
                self._lock.acquire()
                self._voice_channels[voice_channel] += 1
                self._lock.release()

    async def clear(self, text_channel: discord.TextChannel):
        """
        Clear all requests for the specified text channel.
        :param text_channel:
        """
        self._lock.acquire()
        for item in self._request_queues[text_channel]._queue:
            word, message, reverse, text_to_speech = item

            # Remove voice channel requirement for this request
            voice_state = message.author.voice
            voice_channel = None if voice_state is None else voice_state.channel
            if not text_to_speech:
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


class MessageQueue:

    def __init__(self, client, ffmpeg_path):
        """
        This class represents a single request queue. These are created by the DefinitionResponseManager.
        :param client:
        :param ffmpeg_path:
        """
        self._ffmpeg_path = ffmpeg_path
        self._client = client
        self._queue = collections.deque()
        self._lock = threading.Lock()
        self._condition = threading.Condition(self._lock)
        threading.Thread(target=self.run).start()

        # The voice channel that we are currently connected to
        self._voice_channel = None
        self._voice_client = None
        self._voice_lock = threading.Lock()

        self._speaking = True

    def add(self, word, message, reverse=False, text_to_speech=False):
        self._lock.acquire()
        self._queue.append((word, message, reverse, text_to_speech))
        self._condition.notify()
        self._lock.release()

    def run(self):
        print('Started queue processor')
        while True:

            # Wait for an item to enter the queue
            print('Waiting for new items')
            self._lock.acquire()
            if len(self._queue) == 0:
                self._condition.wait()
            self._lock.release()

            print('Processing', len(self._queue), 'items')

            while len(self._queue) > 0:
                word, message, reverse, text_to_speech = self._queue.popleft()

                if text_to_speech:
                    voice_state = message.author.voice
                    voice_channel = None if voice_state is None else voice_state.channel
                else:
                    voice_channel = None
                self._voice_channel = voice_channel

                self._process_definition_request(word, message, reverse=reverse, text_to_speech=text_to_speech)

                # async def f():
                #    async with message.channel.typing():
                #        self._client.process_definition_request(word, message, reverse=reverse)
                # asyncio.run_coroutine_threadsafe(f(), self._client.loop)

                if voice_channel is not None:
                    self._client._definition_response_manager._lock.acquire()
                    self._client._definition_response_manager._voice_channels[voice_channel] -= 1
                    self._client._definition_response_manager._lock.release()

                    # If we don't need this voice channel anymore, disconnect from it
                    if self._client._definition_response_manager._voice_channels[voice_channel] == 0:
                        asyncio.run_coroutine_threadsafe(self._client.leave_voice_channel(voice_channel), self._client.loop)

            print('Finished queue')

    def _process_definition_request(self, word, message, reverse=False, text_to_speech=False):
        """

            :param word:
            :param message:
            :param reverse:
            :return:
            """
        # Get definitions
        response = get_definition(word)
        print('RESPONSE:', response, response.content)
        if response.status_code != 200:
            self._client.sync(utils.send_split(f'__**{word}**__\nI don\'t know that word.', message.channel))
            return

        try:
            definitions = response.json()
        except ValueError:  # Catch a ValueError here because sometimes requests uses simplejson instead of json as a backend
            self._client.sync(utils.send_split(f'__**{word}**__\nThere was a problem finding word.', message.channel))
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

        if voice_channel is not None:
            chunks = self.text_to_speech_pcm(tts_input)

        # Send text chat reply
        self._client.sync(utils.send_split(reply, message.channel))

        # Send voice channel reply
        if voice_channel is not None:

            # Join voice channel
            self._voice_lock.acquire()
            voice_client = self._client.sync(self._client.join_voice_channel(voice_channel)).result()
            self._voice_client = voice_client
            self._voice_lock.release()

            # Speak
            for chunk in chunks:
                file = io.BytesIO()
                file.write(chunk)
                voice_client.play(BytesIOPCMAudio(file, executable=str(self._ffmpeg_path)))

                while voice_client.is_playing() and self._speaking:
                    time.sleep(1)
                if not self._speaking:
                    self._speaking = True
                    voice_client.stop()
                    self._client.sync(utils.send_split(f'Skipping to next word.', message.channel))

        self._voice_channel = None

    def clear(self):
        self._queue.clear()

    async def stop(self):
        self.clear()
        await self._client.leave_voice_channel(self._voice_channel)

    def next(self):
        self._speaking = False

    def __repr__(self):
        return str(self._queue)

    def text_to_speech_pcm(self, text):
        # Instantiates a client
        client = texttospeech.TextToSpeechClient()

        # Build the voice request, select the language code ("en-US") and the ssml
        # voice gender ("neutral")
        voice = texttospeech.VoiceSelectionParams(
            language_code="en-US", ssml_gender=texttospeech.SsmlVoiceGender.NEUTRAL
        )

        # Select the type of audio file you want returned
        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.LINEAR16,
            sample_rate_hertz=48000
        )

        content = []

        messages = split(text, 500)
        for message in messages:
            print('PROCESS:', message)

            # Set the text input to be synthesized
            synthesis_input = texttospeech.SynthesisInput(text=message)

            # Perform the text-to-speech request on the text input with the selected
            # voice parameters and audio file type
            response = client.synthesize_speech(
                input=synthesis_input, voice=voice, audio_config=audio_config
            )

            content.append(response.audio_content)

        return content


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
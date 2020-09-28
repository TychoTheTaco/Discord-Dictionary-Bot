import asyncio
import collections
import threading
import time
from gtts import gTTS
import discord
import pathlib
import requests
import utils
import re


def get_definition(word):
    return requests.get('https://owlbot.info/api/v2/dictionary/' + word.replace(' ', '%20') + '?format=json')


class DefinitionRequest:

    def __init__(self, word, message, reverse=False, text_to_speech=False, language='en-us'):
        self.word = word
        self.message = message
        self.reverse = reverse
        self.text_to_speech = text_to_speech
        self.language = language


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

    def add(self, definition_request: DefinitionRequest):
        """
        Add a request
        :param word:
        :param message:
        :param reverse:
        :param text_to_speech:
        :return:
        """
        message = definition_request.message
        text_channel = message.channel

        # Add request to queue
        if text_channel not in self._request_queues:
            self._request_queues[text_channel] = MessageQueue(self._client, self._ffmpeg_path)

        self._request_queues[text_channel].add(definition_request)

        # Add voice channel
        if definition_request.text_to_speech:
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

    def add(self, definition_request: DefinitionRequest):
        self._lock.acquire()
        self._queue.append(definition_request)
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
                definition_request = self._queue.popleft()

                if definition_request.text_to_speech:
                    voice_state = definition_request.message.author.voice
                    voice_channel = None if voice_state is None else voice_state.channel
                else:
                    voice_channel = None
                self._voice_channel = voice_channel

                self._process_definition_request(definition_request)

                #async def f():
                #    async with message.channel.typing():
                #        self._client.process_definition_request(word, message, reverse=reverse)
                #asyncio.run_coroutine_threadsafe(f(), self._client.loop)

                if voice_channel is not None:
                    self._client._definition_response_manager._lock.acquire()
                    self._client._definition_response_manager._voice_channels[voice_channel] -= 1
                    self._client._definition_response_manager._lock.release()

                    # If we don't need this voice channel anymore, disconnect from it
                    if self._client._definition_response_manager._voice_channels[voice_channel] == 0:
                        asyncio.run_coroutine_threadsafe(self._client.leave_voice_channel(voice_channel), self._client.loop)


            print('Finished queue')

    def say(self, text: str, text_channel: discord.TextChannel, voice_channel=None, language='en-us', tts_input=None):

        # Remove invalid characters for text-to-speech
        if tts_input is None:
            tts_input = re.sub(r'[^A-Za-z0-9 \\.,]+', '', text)

        # Generate text to speech
        if voice_channel is not None:
            try:
                tts = gTTS(tts_input, lang=language)
            except ValueError:
                self._client.sync(utils.send_split(f'That language is not supported.', text_channel))
                return
            urls = tts.get_urls()

        # Send text chat reply
        self._client.sync(utils.send_split(text, text_channel))

        # Send voice channel reply
        if voice_channel is not None:

            # Join voice channel
            self._voice_lock.acquire()
            voice_client = self._client.sync(self._client.join_voice_channel(voice_channel)).result()
            self._voice_client = voice_client
            self._voice_lock.release()

            # Speak
            try:
                for url in urls:
                    voice_client.play(discord.FFmpegPCMAudio(url, executable=str(self._ffmpeg_path), options='-loglevel panic'))
                    while voice_client.is_playing() and self._speaking:
                        time.sleep(1)
                    if not self._speaking:
                        self._speaking = True
                        voice_client.stop()
                        self._client.sync(utils.send_split(f'Skipping to next word.', text_channel))
                        break
            except discord.errors.ClientException:
                pass

        self._voice_channel = None

    def _process_definition_request(self, definition_request: DefinitionRequest):
        """

            :param word:
            :param message:
            :param reverse:
            :return:
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
        print('RESPONSE:', response, response.content)
        if response.status_code != 200:
            self.say(f'__**{word}**__\nI don\'t know that word.', message.channel, voice_channel=voice_channel, language=language, tts_input=f'{word}. I don\'t know that word.')
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

        self.say(reply, message.channel, voice_channel=voice_channel, language=language, tts_input=tts_input)

    def clear(self):
        self._queue.clear()

    async def stop(self):
        self.clear()
        await self._client.leave_voice_channel(self._voice_channel)

    def next(self):
        self._speaking = False

    def __repr__(self):
        return str(self._queue)

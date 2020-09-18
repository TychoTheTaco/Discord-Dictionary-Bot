import discord
import requests
import time
from gtts import gTTS
import pathlib
import json
import threading
import asyncio
import collections

PROJECT_ROOT = pathlib.Path('../')

PREFIX = '!'
TOKEN_FILE_PATH = pathlib.Path(PROJECT_ROOT, 'token.txt')


def get_token(path='token.txt'):
    with open(path) as file:
        return file.read()


def get_definition(word):
    print('GET DEF:', word)
    return requests.get('https://owlbot.info/api/v2/dictionary/' + word.replace(' ', '%20') + '?format=json')


class DefinitionResponseManager:

    def __init__(self, client):
        """
        This class is responsible for responding to user requests for definitions.
        """
        #
        self._client = client

        # Each text channel will have its own request queue to allow simultaneous responses across channels
        self._request_queues = {}

        # Keep track of which voice channels we need to respond to. This way we can leave the channel only when we have finished all requests for that channel
        self._voice_channels = collections.defaultdict(int)

        # Lock used to synchronize 'self._voice_channels'
        self._lock = threading.Lock()

    def add(self, word, message: discord.Message, reverse=False):
        """
        Add a request
        :param word:
        :param message:
        :return:
        """
        text_channel = message.channel
        voice_state = message.author.voice
        voice_channel = None if voice_state is None else voice_state.channel

        # Add request to queue
        if text_channel not in self._request_queues:
            self._request_queues[text_channel] = MessageQueue(self._client)
        self._request_queues[text_channel].add(word, message, reverse=reverse)

        # Add voice channel
        if voice_channel is not None:
            self._lock.acquire()
            self._voice_channels[voice_channel] += 1
            self._lock.release()


class MessageQueue:

    def __init__(self, client):
        self._client = client
        self._queue = collections.deque()
        self._lock = threading.Lock()
        self._condition = threading.Condition(self._lock)
        threading.Thread(target=self.run).start()

    def add(self, word, message, reverse=False):
        self._lock.acquire()
        self._queue.append((word, message, reverse))
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
            print('QUEUE:', self._client._definition_response_manager._request_queues)
            print('VOICE CHANNELS:', self._client._definition_response_manager._voice_channels)

            while len(self._queue) > 0:
                word, message, reverse = self._queue.pop()

                voice_state = message.author.voice
                voice_channel = None if voice_state is None else voice_state.channel

                #with message.channel.typing():
                self._client.process_definition_request(word, message, reverse=reverse)

                if voice_channel is not None:
                    self._client._definition_response_manager._lock.acquire()
                    self._client._definition_response_manager._voice_channels[voice_channel] -= 1
                    self._client._definition_response_manager._lock.release()

                    # If we don't need this voice channel anymore, disconnect from it
                    if self._client._definition_response_manager._voice_channels[voice_channel] == 0:
                        asyncio.run_coroutine_threadsafe(client.leave_voice_channel(voice_channel), client.loop)


                print('QUEUE:', self._client._definition_response_manager._request_queues)
                print('VOICE CHANNELS:', self._client._definition_response_manager._voice_channels)

            print('Finished queue')

    def __repr__(self):
        return str(self._queue)


class DictionaryBotClient(discord.Client):

    def __init__(self, *, loop=None, **options):
        super().__init__(loop=loop, **options)
        self._definition_response_manager = DefinitionResponseManager(self)

    async def on_ready(self):
        print('Logged on as {0}!'.format(self.user))

    async def on_message(self, message):

        # Ignore our own messages
        if message.author == client.user:
            return

        # Check for prefix
        if not message.content.startswith(PREFIX):
            return

        # Parse command
        command = message.content[1:].lower().split(' ')

        if command[0] in ['define', 'd', 'b']:

            # Extract word from command
            word = ' '.join(command[1:])

            # Add word to the queue
            #add(word, message)
            self._definition_response_manager.add(word, message, command[0] == 'b')
            print('Ready.')

        elif command[0] in ['stop', 's']:
            pass
            # Clear word queue and leave voice channel

    async def join_voice_channel(self, voice_channel: discord.VoiceChannel) -> discord.VoiceClient:
        """
        Connect to the specified voice channel if we are not already connected.
        :param voice_channel: The voice channel to connect to.
        :return: A 'discord.VoiceClient' representing our voice connection.
        """
        # Check if we are already connected to this voice channel
        for voice_client in self.voice_clients:
            print(voice_client)
            if voice_client.channel == voice_channel:
                return voice_client

        # Connect to the voice channel
        return await voice_channel.connect()

    async def leave_voice_channel(self, voice_channel: discord.VoiceChannel) -> None:
        for voice_client in self.voice_clients:
            if voice_client.channel == voice_channel:
                await voice_client.disconnect()

    def process_definition_request(self, word, message, reverse=False):
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
            asyncio.run_coroutine_threadsafe(message.channel.send('That\'s not a word bruh'), self.loop)
            return

        try:
            definitions = response.json()
            print('DEFINITIONS:', definitions)
        except json.decoder.JSONDecodeError:
            asyncio.run_coroutine_threadsafe(message.channel.send('There was a problem finding that word'), self.loop)
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
            tts_input += f'{i + 1}, {word_type}, {definition_text}'

        # Generate text-to-speech
        voice_state = message.author.voice
        voice_channel = None if voice_state is None else voice_state.channel
        if voice_channel is not None:
            # Create text to speech mp3
            print(tts_input)
            tts = gTTS(tts_input)
            urls = tts.get_urls()
            print('URLS:', urls)

        # Send text chat reply
        asyncio.run_coroutine_threadsafe(message.channel.send(reply), self.loop)

        # Send voice channel reply
        if voice_channel is not None:

            # Join voice channel
            voice_client = asyncio.run_coroutine_threadsafe(self.join_voice_channel(voice_channel), self.loop).result()
            print('CLIENT:', voice_client)

            # Speak
            for url in urls:
                voice_client.play(discord.FFmpegPCMAudio(url, executable=str(pathlib.Path(PROJECT_ROOT, 'ffmpeg-20200831-4a11a6f-win64-static/bin/ffmpeg.exe'))))
                while voice_client.is_playing():
                    time.sleep(1)


client = DictionaryBotClient()
client.run(get_token(path='../token.txt'))

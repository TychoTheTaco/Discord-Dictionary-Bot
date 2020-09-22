import discord
import requests
import time
from gtts import gTTS
import pathlib
import json
import threading
import asyncio
import collections
import argparse

PROJECT_ROOT = pathlib.Path('../')
TOKEN_FILE_PATH = pathlib.Path(PROJECT_ROOT, 'token.txt')
FFMPEG_EXE_PATH = None  # Set by argparse

PREFIX = '.'


def get_token(path='token.txt'):
    with open(path) as file:
        return file.read()


def get_definition(word):
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

    async def clear(self, text_channel: discord.TextChannel):
        """
        Clear all requests for the specified text channel.
        :param text_channel:
        """
        self._lock.acquire()
        for item in self._request_queues[text_channel]._queue:
            word, message, reverse = item

            # Remove voice channel requirement for this request
            voice_state = message.author.voice
            voice_channel = None if voice_state is None else voice_state.channel
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


class MessageQueue:

    def __init__(self, client):
        self._client = client
        self._queue = collections.deque()
        self._lock = threading.Lock()
        self._condition = threading.Condition(self._lock)
        threading.Thread(target=self.run).start()

        # The voice channel that we are currently connected to
        self._voice_channel = None

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
                word, message, reverse = self._queue.popleft()

                voice_state = message.author.voice
                voice_channel = None if voice_state is None else voice_state.channel
                self._voice_channel = voice_channel

                self._client.process_definition_request(word, message, reverse=reverse)

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


                print('QUEUE:', self._client._definition_response_manager._request_queues)
                print('VOICE CHANNELS:', self._client._definition_response_manager._voice_channels)

            print('Finished queue')

    def clear(self):
        self._queue.clear()

    async def stop(self):
        self.clear()
        await self._client.leave_voice_channel(self._voice_channel)

    def __repr__(self):
        return str(self._queue)


class Command:

    def __init__(self, name, aliases=None, description='', arg_format=''):
        self._name = name
        if aliases is None:
            self._aliases = []
        else:
            self._aliases = aliases
        self._description = description
        self._arg_format = arg_format

    def matches(self, string):
        return string in [self._name] + self._aliases


class DictionaryBotClient(discord.Client):

    def __init__(self, *, loop=None, **options):
        super().__init__(loop=loop, **options)
        self._commands = [
            Command('define', aliases=['d'], description='Prints the definition of the word in chat and if you are in a voice channel, reads it out.', arg_format='<word>'),
            Command('help', aliases=['h'], description='Shows you this help message.'),
            Command('stop', aliases=['s'], description='Makes this bot stop talking and removes all definition requests.')
        ]
        self._definition_response_manager = DefinitionResponseManager(self)

    async def on_ready(self):
        print(f'Logged on as {self.user}!')

    async def on_message(self, message: discord.Message):

        # Ignore our own messages
        if message.author == self.user:
            return

        # Check for prefix
        if not message.content.startswith(PREFIX):
            return

        # Parse command
        command_input = message.content[1:].lower().split(' ')

        for command in self._commands:
            if command.matches(command_input[0]):
                if command._name == 'help':
                    await message.channel.send(self._get_help_message())
                elif command._name == 'define':
                    # Extract word from command
                    word = ' '.join(command_input[1:])

                    # Add word to the queue
                    self._definition_response_manager.add(word, message, command_input[0] == 'b')
                elif command._name == 'stop':
                    # Clear word queue
                    await self._definition_response_manager.clear(message.channel)
                break


        print('Ready.')

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
            asyncio.run_coroutine_threadsafe(message.channel.send(f'__**{word}**__\nI don\'t know that word.'), self.loop)
            return

        try:
            definitions = response.json()
            print('DEFINITIONS:', definitions)
        except ValueError:
            asyncio.run_coroutine_threadsafe(message.channel.send('There was a problem finding that word.'), self.loop)
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

            # Speak
            try:
                for url in urls:
                    voice_client.play(discord.FFmpegPCMAudio(url, executable=str(FFMPEG_EXE_PATH)))
                    while voice_client.is_playing():
                        time.sleep(1)
            except discord.errors.ClientException:
                pass

    def _get_help_message(self) -> str:
        string = '__Available Commands__\n'
        for command in self._commands:
            string += f'**{command._name}** {command._arg_format}\n'
            string += f'        {command._description}\n'

        return string


if __name__ == '__main__':

    # Parse arguments
    parser = argparse.ArgumentParser()
    parser.add_argument('-t', help='Token to use when running the bot.', dest='token', default=None)
    parser.add_argument('-f', help='Path to ffmpeg executable', dest='ffmpeg_exe_path', default='ffmpeg')
    args = parser.parse_args()

    FFMPEG_EXE_PATH = args.ffmpeg_exe_path

    # Create client
    client = DictionaryBotClient()

    # Start client
    if args.token is None:
        client.run(get_token(path='../token.txt'))
    else:
        client.run(args.token)

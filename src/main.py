import discord
import requests
import time
from gtts import gTTS
import pathlib
import json
import threading
from queue import Queue
import asyncio

PROJECT_ROOT = pathlib.Path('../')

PREFIX = '!'
TOKEN_FILE_PATH = pathlib.Path(PROJECT_ROOT, 'token.txt')


def get_token(path='token.txt'):
    with open(path) as file:
        return file.read()


def get_definition(word):
    print('GET DEF:', word)
    return requests.get('https://owlbot.info/api/v2/dictionary/' + word.replace(' ', '%20') + '?format=json')


word_queues = {}
vc_requests = {}


class MessageQueue:

    def __init__(self):
        self._queue = Queue()
        self._lock = threading.Lock()
        self._condition = threading.Condition(self._lock)
        threading.Thread(target=self.run).start()

    def add(self, word, message):
        self._lock.acquire()
        self._queue.put((word, message))
        self._condition.notify()
        self._lock.release()

    def run(self):
        print('Started queue processor')
        while True:

            # Wait for an item to enter the queue
            print('Waiting for new items')
            self._lock.acquire()
            if self._queue.empty():
                self._condition.wait()
            self._lock.release()

            print('Processing', self._queue.qsize(), 'items')

            while not self._queue.empty():
                word, message = self._queue.get()

                #with message.channel.typing():
                process_word(word, message)

            print('Finished queue')


def add(word, message):
    text_channel = message.channel
    voice_state = message.author.voice
    voice_channel = None if voice_state is None else voice_state.channel

    if text_channel not in word_queues:
        word_queues[text_channel] = MessageQueue()
    word_queues[text_channel].add(word, message)
    print(word_queues)

    if voice_channel is not None:
        if voice_channel not in vc_requests:
            vc_requests[voice_channel] = 0
        vc_requests[voice_channel] += 1
    print(vc_requests)


def process_word(word, message, reverse=False):
    """

    :param word:
    :param message:
    :param reverse:
    :return:
    """
    # Get definitions
    response = get_definition(word)
    print('RETURN:', response)
    if response.status_code != 200:
        asyncio.run_coroutine_threadsafe(message.channel.send('That\'s not a word bruh'), loop)
        return

    try:
        print('RESPONSE:', response)
        definitions = response.json()
        print('DEFINITIONS:', definitions)
    except json.decoder.JSONDecodeError:
        asyncio.run_coroutine_threadsafe(message.channel.send('There was a problem finding that word'), loop)
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
    asyncio.run_coroutine_threadsafe(message.channel.send(reply), loop)

    # Send voice channel reply
    if voice_channel is not None:

        # Join voice channel
        voice_client = asyncio.run_coroutine_threadsafe(voice_channel.connect(), loop).result()

        # Speak
        for url in urls:
            voice_client.play(discord.FFmpegPCMAudio(url, executable=str(pathlib.Path(PROJECT_ROOT, 'ffmpeg-20200831-4a11a6f-win64-static/bin/ffmpeg.exe'))))
            while voice_client.is_playing():
                time.sleep(1)

        # Disconnect from voice channel
        asyncio.run_coroutine_threadsafe(voice_client.disconnect(), loop)


loop = asyncio.get_event_loop()


class Client(discord.Client):

    async def on_ready(self):
        print('Logged on as {0}!'.format(self.user))
        print(loop is asyncio.get_event_loop())

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
            add(word, message)


client = Client()
client.run(get_token(path='../token.txt'))

import discord
import requests
import time
from gtts import gTTS
import pathlib
import io
import json

PROJECT_ROOT = pathlib.Path('../')

PREFIX = '!'
TOKEN_FILE_PATH = pathlib.Path(PROJECT_ROOT, 'token.txt')


def get_token(path='token.txt'):
    with open(path) as file:
        return file.read()


def get_definition(word):
    print('GET DEF:', word)
    return requests.get('https://owlbot.info/api/v2/dictionary/' + word.replace(' ', '%20') + '?format=json')


async def process_word(word, message, reverse=False):
    """

    :param word:
    :param message:
    :return:
    """
    # Get definitions
    response = get_definition(word)
    print('RETURN:', response)
    if response.status_code != 200:
        await message.channel.send('That\'s not a word bruh')
        return

    try:
        definitions = response.json()
        print('DEFINITIONS:', definitions)
    except json.decoder.JSONDecodeError:
        await message.channel.send('There was a problem finding that word')
        return

    # Send text chat reply
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

    await message.channel.send(reply)

    # Create text to speech mp3
    print(tts_input)
    tts = gTTS(tts_input)
    urls = tts.get_urls()
    print('URLS:', urls)

    # Join voice channel
    voice_channel = message.author.voice.channel
    if voice_channel is not None:
        voice_client = await voice_channel.connect()

        for url in urls:
            voice_client.play(discord.FFmpegPCMAudio(url, executable=str(pathlib.Path(PROJECT_ROOT, 'ffmpeg-20200831-4a11a6f-win64-static/bin/ffmpeg.exe'))))
            while voice_client.is_playing():
                time.sleep(1)
        await voice_client.disconnect()


class Client(discord.Client):

    TTS_CACHE = pathlib.Path(PROJECT_ROOT, 'ttscache')

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
        print('command:', command)

        if command[0] in ['define', 'd']:

            # Extract word from command
            word = ' '.join(command[1:])
            print('word:', word)

            await process_word(word, message)

        elif command[0] in ['b']:

            # Extract word from command
            word = ' '.join(command[1:])
            print('word:', word)

            await process_word(word, message, reverse=True)


client = Client()
client.run(get_token(path='../token.txt'))

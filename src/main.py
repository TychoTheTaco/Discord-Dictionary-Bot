import discord
import requests
import time
from gtts import gTTS
import pathlib

PROJECT_ROOT = pathlib.Path('../')

PREFIX = '!'
TOKEN_FILE_PATH = pathlib.Path(PROJECT_ROOT, 'token.txt')


def get_token(path='token.txt'):
    with open(path) as file:
        return file.read()


def get_definition(word):
    return requests.get('https://owlbot.info/api/v2/dictionary/' + word.replace(' ', '%20') + '?format=json')


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

            # Replace spaces
            response = get_definition(word)
            if response.status_code is not 200:
                await message.channel.send('That\'s not a word bruh')
            else:
                definitions = response.json()

                # Send text chat reply
                print('DEFINE: ', definitions)
                reply = f'__**{word}**__\n'
                tts_input = f'{word}.'
                for i, definition in enumerate(definitions):
                    reply += f'**[{i + 1}]** ({definition["type"]})\n' + definition['definition'] + '\n'
                    tts_input += f'{i + 1}. {definition["type"]}. {definition["definition"]}'
                await message.channel.send(reply)

                # Create text to speech mp3
                mp3_path = pathlib.Path(Client.TTS_CACHE, 'reply.mp3')
                tts = gTTS(tts_input)
                tts.save(str(mp3_path))

                # Join voice channel
                connected = message.author.voice
                if connected:
                    voice_channel = await connected.channel.connect()

                    voice_channel.play(discord.FFmpegPCMAudio(str(mp3_path), executable=str(pathlib.Path(PROJECT_ROOT, 'ffmpeg-20200831-4a11a6f-win64-static/bin/ffmpeg.exe'))))
                    while voice_channel.is_playing():
                        time.sleep(1)
                    await voice_channel.disconnect()


client = Client()
client.run(get_token(path='../token.txt'))

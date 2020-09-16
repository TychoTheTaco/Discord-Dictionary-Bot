import discord
import requests
import time
from gtts import gTTS


PREFIX = '!'
TOKEN_FILE_PATH = 'token.txt'


def get_token(path='token.txt'):
    with open(path) as file:
        return file.read()


class Client(discord.Client):

    async def on_ready(self):
        print('Logged on as {0}!'.format(self.user))

    async def on_message(self, message):

        # Ignore our own messages
        if message.author == client.user:
            return

        # Check for prefix
        if not message.content.startswith(PREFIX):
            return

        print('Message from {0.author}: {0.content}'.format(message))

        # Parse command
        command = message.content[1:].lower().split(' ')
        print('command:', command)

        if command[0] in ['define', 'd']:
            word = ' '.join(command[1:])
            print('word:', word)

            # Replace spaces
            w = word.replace(' ', '%20')
            print(w)
            response = requests.get(f'https://owlbot.info/api/v2/dictionary/{w}?format=json')
            if response.status_code is not 200:
                await message.channel.send('That\'s not a word bruh')
            else:
                definitions = response.json()
                print('DEFINE: ', definitions)
                reply = ''
                for i, definition in enumerate(definitions):
                    reply += f'[{i}]: ' + definition['definition'] + '\n'
                await message.channel.send(reply)

                # Create text to speech mp3
                tts = gTTS(word + '.' + reply)
                tts.save('reply.mp3')

                # Join voice channel
                connected = message.author.voice
                if connected:
                    voice_channel = await connected.channel.connect()

                    voice_channel.play(discord.FFmpegPCMAudio('reply.mp3', executable='A:/Code Projects/Tools/ffmpeg-20200831-4a11a6f-win64-static/bin/ffmpeg.exe'))
                    while voice_channel.is_playing():
                        time.sleep(1)
                    await voice_channel.disconnect()


client = Client()
client.run(get_token())

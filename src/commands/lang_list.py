from commands.command import Command
import discord
import gtts
import utils


class LangListCommand(Command):

    def __init__(self, client: discord.Client):
        super().__init__(client, 'lang', aliases=['l'], description='Shows the list of supported languages for text to speech.')

    def execute(self, message: discord.Message, args: tuple):
        languages = gtts.lang.tts_langs()
        reply = '__Supported Languages__\n'
        for k, v in languages.items():
            reply += f'{v}: {k}\n'
        self.client.sync(utils.send_split(reply, message.channel))

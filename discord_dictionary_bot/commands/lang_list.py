import io
import discord
from discord_slash import SlashContext
from google.cloud import texttospeech
import gtts
import argparse
from contextlib import redirect_stderr

from .command import Command, Context
from ..discord_bot_client import DiscordBotClient
from .. import utils


class LangListCommand(Command):

    def __init__(self, client: DiscordBotClient):
        super().__init__(
            client,
            'languages',
            aliases=['l', 'lang'],
            description='Shows the list of supported languages for text to speech.',
            usage='[-v]',
            slash_command_options=[
                {
                    'name': 'verbose',
                    'description': 'Prints all supported languages (This will spam the chat).',
                    'type': 5
                }
            ]
        )

    def execute(self, context: Context, args: tuple):

        try:
            parser = argparse.ArgumentParser()
            parser.add_argument('-v', action='store_true', default=False, dest='verbose', help='Verbose')

            # Parse arguments but suppress stderr output
            stderr_stream = io.StringIO()
            with redirect_stderr(stderr_stream):
                args = parser.parse_args(args)

        except SystemExit:
            self.client.sync(utils.send_split(f'Invalid arguments!\nUsage: `{self.name} {self.usage}`', context.channel))
            return

        # Check if we can embed links in this channel
        if (isinstance(context.channel, discord.DMChannel) or context.channel.guild.me.permissions_in(context.channel).embed_links) and not args.verbose:

            # Send reply
            e = discord.Embed()
            e.title = 'Supported Languages'
            e.url = 'https://cloud.google.com/text-to-speech/docs/voices'
            self.client.sync(context.channel.send(embed=e))

        else:

            client = texttospeech.TextToSpeechClient()
            response = client.list_voices()

            languages = {}
            for voice in response.voices:
                language_code = voice.language_codes[0]
                if language_code not in languages:
                    languages[language_code] = {}
                if voice.ssml_gender not in languages[language_code]:
                    languages[language_code][voice.ssml_gender] = []
                languages[language_code][voice.ssml_gender].append(voice.name)

            codes = gtts.tts.tts_langs()

            def gn(lc: str):
                lc = lc.lower()
                if lc not in codes:
                    s = lc.split('-')
                    if len(s) > 1:
                        return gn(s[0])
                    return 'Unknown'
                return codes[lc]

            GENDER_NAMES = ['unspecified', 'male', 'female', 'neutral']

            # Send reply
            reply = '__Supported Languages__\n'
            for language_code, voices in sorted(languages.items(), key=lambda x: x[0]):
                reply += f'**{gn(language_code)}: ** {language_code}\n'
                if args.verbose:
                    for gender, voice_styles in sorted(voices.items()):
                        reply += f'    **{GENDER_NAMES[gender]}**\n'
                        for voice_style in sorted(voice_styles):
                            reply += f'        {voice_style}\n'
                    reply += '\n'
            self.client.sync(utils.send_split_nf(reply, context.channel, delim='\n[^ ]'))  # TODO: Send this only to the user that requested it

    def execute_slash_command(self, slash_context: SlashContext, args: tuple):
        verbose = False if len(args) < 1 else args[0]

        # Check if we can embed links in this channel
        if (isinstance(slash_context.channel, discord.DMChannel) or slash_context.channel.guild.me.permissions_in(slash_context.channel).embed_links) and not verbose:

            # Send reply
            e = discord.Embed()
            e.title = 'Supported Languages'
            e.url = 'https://cloud.google.com/text-to-speech/docs/voices'
            self.client.sync(slash_context.send(send_type=4, embeds=[e]))  # We cannot send a hidden message with embeds, so this will show for everyone in the channel

        else:

            self.client.sync(slash_context.send(send_type=5))

            client = texttospeech.TextToSpeechClient()
            response = client.list_voices()

            languages = {}
            for voice in response.voices:
                language_code = voice.language_codes[0]
                if language_code not in languages:
                    languages[language_code] = {}
                if voice.ssml_gender not in languages[language_code]:
                    languages[language_code][voice.ssml_gender] = []
                languages[language_code][voice.ssml_gender].append(voice.name)

            codes = gtts.tts.tts_langs()

            def gn(lc: str):
                lc = lc.lower()
                if lc not in codes:
                    s = lc.split('-')
                    if len(s) > 1:
                        return gn(s[0])
                    return 'Unknown'
                return codes[lc]

            GENDER_NAMES = ['unspecified', 'male', 'female', 'neutral']

            # Send reply
            reply = '__Supported Languages__\n'
            for language_code, voices in sorted(languages.items(), key=lambda x: x[0]):
                reply += f'**{gn(language_code)}: ** {language_code}\n'
                if verbose:
                    for gender, voice_styles in sorted(voices.items()):
                        reply += f'    **{GENDER_NAMES[gender]}**\n'
                        for voice_style in sorted(voice_styles):
                            reply += f'        {voice_style}\n'
                    reply += '\n'

            self.client.sync(utils.send_split_nf(reply, slash_context.channel, delim='\n[^ ]'))  # TODO: Send this only to the user that requested it

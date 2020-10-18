from definition_response_manager import DefinitionRequest
from commands.command import Command
import discord
import argparse
import utils
import re
from google.cloud import texttospeech


class DefineCommand(Command):

    def __init__(self, client: discord.client, definition_response_manager, name, aliases=None, description='', secret=False):
        super().__init__(client, name, aliases, description, usage='[-v] [-lang <language_code>] <word>', secret=secret)
        self._definition_response_manager = definition_response_manager

        # Get a list of supported languages
        client = texttospeech.TextToSpeechClient()
        response = client.list_voices()

        self._languages = set(voice.name for voice in response.voices)
        print(self._languages)

    def execute(self, message: discord.Message, args: tuple):
        try:
            parser = argparse.ArgumentParser()
            parser.add_argument('word', nargs='+')
            parser.add_argument('-v', action='store_true', default=False, dest='text_to_speech')
            parser.add_argument('-lang', '-l', dest='language', default=self.client.properties.get(message.channel, 'language'))
            args = parser.parse_args(args)
        except SystemExit:
            self.client.sync(utils.send_split(f'Invalid arguments!\nUsage: `{self.name} {self.usage}`', message.channel))
            return

        # Extract word from arguments
        word = ' '.join(args.word).strip()

        # Check for non-word characters
        pattern = re.compile('(?:[^ \\w]|\\d)')
        if pattern.search(word) is not None:
            self.client.sync(utils.send_split(f'That\'s not a word.', message.channel))
            return

        # TODO: Find closest matching language
        if args.language not in self._languages:
            for language_code in self._languages:
                if language_code.startswith(args.language):
                    args.language = language_code
                    self.client.sync(utils.send_split(f'**Unknown language. Assuming it\'s** `{args.language}`', message.channel))
                    break

        # Add request to queue
        self.send_request(word, message, False, args.text_to_speech, language=args.language)

    def send_request(self, word, message, reverse, text_to_speech, language):
        self._definition_response_manager.add(DefinitionRequest(word, message, reverse=reverse, text_to_speech=text_to_speech, language=language))

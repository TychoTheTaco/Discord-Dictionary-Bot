from commands.command import Command
import discord
import argparse
from definition_response_manager import DefinitionRequest
import utils


class DefineReverseCommand(Command):

    def __init__(self, client: discord.Client, definition_response_manager):
        super().__init__(client, 'b', secret=True)
        self._definition_response_manager = definition_response_manager

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
        word = ' '.join(args.word)

        # Add request to queue
        self._definition_response_manager.add(DefinitionRequest(word, message, reverse=True, text_to_speech=args.text_to_speech, language=args.language))

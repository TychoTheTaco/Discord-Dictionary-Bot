from commands.command import Command
import discord


class DefineReverseCommand(Command):

    def __init__(self, client: discord.Client, definition_response_manager):
        super().__init__(client, 'b', secret=True)
        self._definition_response_manager = definition_response_manager

    def execute(self, message: discord.Message, args: tuple):
        # Check for text to speech option
        text_to_speech = len(args) > 1 and args[0] == '-v'

        # Extract word from command
        word = ' '.join(args[int(text_to_speech):])

        # Add request to queue
        self._definition_response_manager.add(word, message, reverse=True, text_to_speech=text_to_speech)

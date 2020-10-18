from commands.define import DefineCommand
import discord


class DefineReverseCommand(DefineCommand):

    def __init__(self, client: discord.Client, definition_response_manager):
        super().__init__(client, definition_response_manager, 'b', secret=True)

    def send_request(self, word, message, reverse, text_to_speech, language):
        super().send_request(word, message, True, text_to_speech, language)

from commands.define import DefineCommand
from discord_bot_client import DiscordBotClient


class DefineReverseCommand(DefineCommand):

    def __init__(self, client: DiscordBotClient, definition_response_manager):
        super().__init__(client, definition_response_manager, 'b', secret=True)

    def send_request(self, user, word, message, reverse, text_to_speech, language):
        super().send_request(user, word, message, True, text_to_speech, language)

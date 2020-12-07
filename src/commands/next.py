from commands.command import Command
import discord


class NextCommand(Command):

    def __init__(self, client: 'dictionary_bot_client.DictionaryBotClient', definition_response_manager):
        super().__init__(client, 'next', aliases=['n'], description='If the bot is currently reading out a definition, this will make it skip to the next one.')
        self._definition_response_manager = definition_response_manager

    def execute(self, message: discord.Message, args: tuple):
        self._definition_response_manager.next(message.channel)

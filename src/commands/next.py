from commands.command import Command, Context

from discord_bot_client import DiscordBotClient


class NextCommand(Command):

    def __init__(self, client: DiscordBotClient, definition_response_manager):
        super().__init__(client, 'next', aliases=['n'], description='If the bot is currently reading out a definition, this will make it skip to the next one.')
        self._definition_response_manager = definition_response_manager

    def execute(self, context: Context, args: tuple):
        self._definition_response_manager.next(context.channel)

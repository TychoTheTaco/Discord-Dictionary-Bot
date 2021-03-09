from discord_slash import SlashContext

from .command import Command, Context
from ..discord_bot_client import DiscordBotClient
from ..analytics import log_command


class StopCommand(Command):

    def __init__(self, client: DiscordBotClient, definition_response_manager):
        super().__init__(client, 'stop', aliases=['s'], description='Makes this bot stop talking and removes all definition requests.', slash_command_options=[])
        self._definition_response_manager = definition_response_manager

    @log_command(False)
    async def execute(self, context: Context, args: tuple) -> None:
        self._definition_response_manager.stop(context.channel)

    @log_command(True)
    async def execute_slash_command(self, slash_context: SlashContext, args: tuple) -> None:
        await self.execute(slash_context, args)  # SlashContext has a channel attribute so this is OK

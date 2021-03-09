import discord
from discord_slash import SlashContext

from . import Context
from .define import DefineCommand
from ..discord_bot_client import DiscordBotClient
from ..analytics import log_command


class DefineReverseCommand(DefineCommand):

    def __init__(self, client: DiscordBotClient, definition_response_manager):
        super().__init__(client, definition_response_manager, 'befine', aliases=['b'], secret=True)

    def _add_request(self, user: discord.User, word, channel: discord.abc.Messageable, reverse, text_to_speech, language):
        super()._add_request(user, word, channel, True, text_to_speech, language)

    @log_command(False)
    async def execute(self, context: Context, args: tuple) -> None:
        return await super().execute(context, args)

    @log_command(True)
    async def execute_slash_command(self, slash_context: SlashContext, args: tuple) -> None:
        return await super().execute_slash_command(slash_context, args)

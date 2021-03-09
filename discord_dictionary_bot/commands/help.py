from discord_slash import SlashContext

from .command import Command, Context
from .. import utils
from ..discord_bot_client import DiscordBotClient
from ..analytics import log_command


class HelpCommand(Command):

    def __init__(self, client: DiscordBotClient):
        super().__init__(client, 'help', aliases=['h'], description='Shows you this help message.', slash_command_options=[])

    @log_command(False)
    async def execute(self, context: Context, args: tuple) -> None:
        reply = '__Available Commands__\n'
        for command in sorted(self.client.commands, key=lambda x: x.name):
            if not command.secret:
                reply += f'**{command.name}**'
                if len(command.usage) > 0:
                    reply += f' `{command.usage}`'
                reply += '\n'
                reply += f'{command.description}\n'
        await utils.send_split(reply, context.channel)

    @log_command(True)
    async def execute_slash_command(self, slash_context: SlashContext, args: tuple) -> None:
        reply = '__Available Commands__\n'
        for command in sorted(self.client.commands, key=lambda x: x.name):
            if not command.secret:
                reply += f'**/{command.name}**'
                reply += '\n'
                reply += f'{command.description}\n'
        await slash_context.send(send_type=3, content=reply, hidden=True)

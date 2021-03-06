from . import Context
from .command import Command
from .. import utils
from ..discord_bot_client import DiscordBotClient


class ActiveServerCountCommand(Command):

    def __init__(self, client: DiscordBotClient):
        super().__init__(client, 'asc', description='Shows the number of servers this bot is active in.', secret=True)

    async def execute(self, context: Context, args: tuple) -> None:
        await utils.send_split(f'Currently active in {len(self.client.guilds)} servers.', context.channel)

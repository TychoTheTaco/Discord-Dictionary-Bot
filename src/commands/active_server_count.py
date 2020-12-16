from commands.command import Command
import discord
import utils

from discord_bot_client import DiscordBotClient


class ActiveServerCountCommand(Command):

    def __init__(self, client: DiscordBotClient):
        super().__init__(client, 'asc', description='Shows the number of servers this bot is active in.', secret=True)

    def execute(self, message: discord.Message, args: tuple):
        self.client.sync(utils.send_split(f'Currently active in {len(self.client.guilds)} servers.', message.channel))

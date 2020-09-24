from commands.command import Command
import discord


class StopCommand(Command):

    def __init__(self):
        super().__init__('stop', aliases=['s'], description='Makes this bot stop talking and removes all definition requests.')

    def execute(self, client: discord.client, message: discord.Message, args: tuple):
        pass

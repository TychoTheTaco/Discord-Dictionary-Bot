from commands.command import Command
import discord


class StopCommand(Command):

    def __init__(self, client: discord.Client):
        super().__init__(client, 'stop', aliases=['s'], description='Makes this bot stop talking and removes all definition requests.')

    def execute(self, message: discord.Message, args: tuple):
        pass

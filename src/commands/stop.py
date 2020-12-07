from commands.command import Command
import discord


class StopCommand(Command):

    def __init__(self, client: discord.Client, definition_response_manager):
        super().__init__(client, 'stop', aliases=['s'], description='Makes this bot stop talking and removes all definition requests.')
        self._definition_response_manager = definition_response_manager

    def execute(self, message: discord.Message, args: tuple):
        self._definition_response_manager.stop(message.channel)

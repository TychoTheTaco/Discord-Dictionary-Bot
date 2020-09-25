from commands.command import Command
import discord


class HelpCommand(Command):

    def __init__(self, client: discord.Client):
        super().__init__(client, 'help', aliases=['h'], description='Shows you this help message.')

    def execute(self, message: discord.Message, args: tuple):
        reply = '__Available Commands__\n'
        for command in self.client.commands:
            reply += f'**{command.name}** {command.usage}\n'
            reply += f'        {command.description}\n'

        self.sync(message.channel.send(reply))

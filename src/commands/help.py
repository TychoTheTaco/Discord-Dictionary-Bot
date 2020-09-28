from commands.command import Command
import discord
import utils


class HelpCommand(Command):

    def __init__(self, client: discord.Client):
        super().__init__(client, 'help', aliases=['h'], description='Shows you this help message.')

    def execute(self, message: discord.Message, args: tuple):
        reply = '__Available Commands__\n'
        for command in self.client.commands:
            if not command.secret:
                reply += f'**{command.name}**'
                if len(command.usage) > 0:
                    reply += f' `{command.usage}`'
                reply += '\n'
                reply += f'{command.description}\n'

        self.client.sync(utils.send_split(reply, message.channel))

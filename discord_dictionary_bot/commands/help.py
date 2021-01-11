from commands.command import Command, Context
import utils


class HelpCommand(Command):

    def __init__(self, client: 'DiscordBotClient'):
        super().__init__(client, 'help', aliases=['h'], description='Shows you this help message.')

    def execute(self, context: Context, args: tuple):
        reply = '__Available Commands__\n'
        for command in sorted(self.client.commands, key=lambda x: x.name):
            if not command.secret:
                reply += f'**{command.name}**'
                if len(command.usage) > 0:
                    reply += f' `{command.usage}`'
                reply += '\n'
                reply += f'{command.description}\n'

        self.client.sync(utils.send_split(reply, context.channel))

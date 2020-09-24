from commands.command import Command
import discord
import asyncio


class HelpCommand(Command):

    def __init__(self):
        super().__init__('help', aliases=['h'], description='Shows you this help message.')

    def execute(self, client: discord.client, message: discord.Message, args: tuple):
        reply = '__Available Commands__\n'
        for command in client.commands:
            reply += f'**{command.name}** {command.usage}\n'
            reply += f'        {command.description}\n'

        asyncio.run_coroutine_threadsafe(message.channel.send(reply), client.loop)

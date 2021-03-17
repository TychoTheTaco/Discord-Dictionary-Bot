from discord.ext import commands
import logging

from ..utils import send_maybe_hidden

# Set up logging
logger = logging.getLogger(__name__)


class Help(commands.Cog):

    @commands.command(name='help', aliases=['h'], help='Shows you a helpful message.')
    async def help(self, context: commands.Context):
        reply = '__**Available Commands**__\n'
        for command in sorted(context.bot.commands, key=lambda x: x.name):
            if not command.hidden:
                reply += f'**{command.name}**'
                if command.usage is not None:
                    reply += f' `{command.usage}`'
                reply += '\n'
                reply += f'{command.help}\n'
        await send_maybe_hidden(context, reply)

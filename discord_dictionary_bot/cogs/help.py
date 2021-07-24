import logging
from typing import Optional

from discord.ext import commands

from ..utils import reply_maybe_hidden

# Set up logging
logger = logging.getLogger(__name__)


class Help(commands.Cog):

    @commands.command(name='help', aliases=['h'], help='Shows you a helpful message.', usage='<command>')
    async def help(self, context: commands.Context, command_name: Optional[str] = None):
        if command_name is None:
            reply = '__**Available Commands**__\n'
            for command in sorted(context.bot.commands, key=lambda x: x.name):
                if not command.hidden:
                    reply += f'**{command.name}**'
                    if command.usage is not None:
                        reply += f' `{command.usage}`'
                    reply += '\n'
                    reply += f'{command.help}\n'
            await reply_maybe_hidden(context, reply)
        elif command_name == 'settings':
            reply = f'**__{command_name}__**\n'
            reply += 'There are 2 groups of settings: **Server settings** and **Channel settings**. Server settings affect all channels in the server, unless they are overridden with channel settings. Channel settings only affect a specific channel and take priority over server settings.\n\n'
            reply += f'View settings: `{command_name} list <scope>`\n'
            reply += '\t`<scope>`: `guild` or `channel`.\n'
            reply += '\n'
            reply += f'To change settings: `{command_name} set <scope> <name> <value>`\n'
            reply += '\t`<scope>`: `guild` or `channel`.\n'
            reply += '\t`<name>`: The name of the setting. See the list below for available settings.\n'
            reply += '\t`<value>`: The value of the setting. See the list below for valid values for each setting.\n'
            reply += '\n'
            reply += f'To remove settings: `{command_name} remove <scope> <name>`\n'
            reply += '\t`<scope>`: `guild` or `channel`.\n'
            reply += '\t`<name>`: The name of the setting. See the list below for available settings.\n'
            reply += '\n'

            reply += 'You can change the following settings:\n\n'

            settings_cog = context.bot.get_cog('Settings')
            scoped_property_manager = settings_cog.scoped_property_manager
            for p in sorted(scoped_property_manager.properties, key=lambda x: x.key):
                reply += f'**{p.key}**\n'
                reply += p.description + '\n\n'

            await reply_maybe_hidden(context, reply)
        else:
            reply = ''
            for command in context.bot.commands:
                if not command.hidden and command_name == command.name:
                    reply += f'**{command.name}**'
                    if command.usage is not None:
                        reply += f' `{command.usage}`'
                    reply += '\n'
                    reply += f'{command.help}\n'
            if len(reply) == 0:
                await reply_maybe_hidden(context, 'That\'s not a command name!')
            else:
                await reply_maybe_hidden(context, reply)

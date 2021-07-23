import logging
from typing import Union, Optional

from discord.ext import commands
from discord_slash import SlashContext
import discord

# Set up logging
logger = logging.getLogger(__name__)


def get_bot_permissions(context: Union[commands.Context, SlashContext]):
    permissions: discord.Permissions = context.channel.guild.me.permissions_in(context.channel)
    permission_names = {
        'send_messages': permissions.send_messages,
        'view_channel': permissions.view_channel,
        'embed_links': permissions.embed_links,
        'connect': permissions.connect,
        'speak': permissions.speak
    }
    return permission_names


async def send_maybe_hidden(context: Union[commands.Context, SlashContext], text: Optional[str] = None, **kwargs):
    try:
        if isinstance(context, SlashContext):
            return await context.send(text, hidden=True, **kwargs)
        return await context.send(text, **kwargs)
    except discord.errors.Forbidden:
        logger.warning(f'Failed to send message! Missing permissions. We have {get_bot_permissions(context)}')


async def reply_maybe_hidden(context: Union[commands.Context, SlashContext], text: Optional[str] = None, **kwargs):
    try:
        if isinstance(context, SlashContext):
            return await context.send(text, hidden=True, **kwargs)
        return await context.reply(text, mention_author=False, **kwargs)
    except discord.errors.Forbidden:
        logger.warning(f'Failed to send message! Missing permissions. We have {get_bot_permissions(context)}')

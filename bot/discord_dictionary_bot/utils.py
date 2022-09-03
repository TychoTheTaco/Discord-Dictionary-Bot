import logging

import discord

# Set up logging
logger = logging.getLogger(__name__)


def get_bot_permissions(channel):
    permissions: discord.Permissions = channel.permissions_for(channel.guild.me)
    permission_names = {
        'send_messages': permissions.send_messages,
        'view_channel': permissions.view_channel,
        'embed_links': permissions.embed_links,
        'connect': permissions.connect,
        'speak': permissions.speak
    }
    return permission_names

import io

from discord_slash import SlashContext

import discord
import argparse
import utils
from properties import Properties
from discord_bot_client import DiscordBotClient
from contextlib import redirect_stderr
#from analytics import log_command


class PropertyCommand:

    def __init__(self, client: DiscordBotClient, properties: Properties):
        super().__init__(
            client,
            'property',
            aliases=['p'],
            description='Change the bot\'s properties for a channel or server. Use this to change the bot prefix, default text-to-speech language, etc.',
            usage='<scope> (list | set <key> <value> | del <key>)',
            slash_command_options=[
                {
                    'name': 'guild',
                    'description': 'Modify guild properties.',
                    'type': 2,
                    'options': [
                        {
                            'name': 'list',
                            'description': 'List guild properties.',
                            'type': 1
                        },
                        {
                            'name': 'set',
                            'description': 'Set guild properties.',
                            'type': 1,
                            'options': [
                                {
                                    'name': 'name',
                                    'description': 'Property name.',
                                    'type': 3,
                                    'required': True
                                },
                                {
                                    'name': 'value',
                                    'description': 'Property value.',
                                    'type': 3,
                                    'required': True
                                }
                            ]
                        }
                    ]
                },
                {
                    'name': 'channel',
                    'description': 'Modify channel properties.',
                    'type': 2,
                    'options': [
                        {
                            'name': 'list',
                            'description': 'List channel properties.',
                            'type': 1
                        },
                        {
                            'name': 'set',
                            'description': 'Set channel properties.',
                            'type': 1,
                            'options': [
                                {
                                    'name': 'name',
                                    'description': 'Property name.',
                                    'type': 3,
                                    'required': True
                                },
                                {
                                    'name': 'value',
                                    'description': 'Property value.',
                                    'type': 3,
                                    'required': True
                                }
                            ]
                        },
                        {
                            'name': 'delete',
                            'description': 'Delete channel properties.',
                            'type': 1,
                            'options': [
                                {
                                    'name': 'name',
                                    'description': 'The name of the property to delete.',
                                    'type': 3,
                                    'required': True
                                }
                            ]
                        }
                    ]
                }
            ]
        )
        self._properties = properties

        @client.slash_command_decorator.subcommand(base=self.name, subcommand_group='guild', name='list')
        async def _on_guild_list_subcommand(slash_context: SlashContext, *args):
            reply = self._get_property_list(slash_context.guild)
            await slash_context.send(send_type=3, content=reply, hidden=True)

        @client.slash_command_decorator.subcommand(base=self.name, subcommand_group='guild', name='set', options=[
            {
                'name': 'name',
                'description': 'Property name.',
                'type': 3,
                'required': True
            },
            {
                'name': 'value',
                'description': 'Property value.',
                'type': 3,
                'required': True
            }
        ])
        async def _on_guild_set_subcommand(slash_context, *args):
            reply = self._set_property(slash_context.guild, args[0], args[1])
            await slash_context.send(send_type=3, content=reply, hidden=True)

        @client.slash_command_decorator.subcommand(base=self.name, subcommand_group='channel', name='list')
        async def _on_channel_list_subcommand(slash_context: SlashContext, *args):
            reply = self._get_property_list(slash_context.channel)
            await slash_context.send(send_type=3, content=reply, hidden=True)

        @client.slash_command_decorator.subcommand(base=self.name, subcommand_group='channel', name='set', options=[
            {
                'name': 'name',
                'description': 'Property name.',
                'type': 3,
                'required': True
            },
            {
                'name': 'value',
                'description': 'Property value.',
                'type': 3,
                'required': True
            }
        ])
        async def _on_channel_set_subcommand(slash_context: SlashContext, *args):
            reply = self._set_property(slash_context.channel, args[0], args[1])
            await slash_context.send(send_type=3, content=reply, hidden=True)

        @client.slash_command_decorator.subcommand(base=self.name, subcommand_group='channel', name='delete', options=[
            {
                'name': 'name',
                'description': 'The name of the property to delete.',
                'type': 3,
                'required': True
            }
        ])
        async def _on_channel_delete_subcommand(slash_context, *args):
            reply = self._delete_property(slash_context.channel, args[0])
            await slash_context.send(send_type=3, content=reply, hidden=True)

    #@log_command(False)
    async def execute(self, context, args: tuple) -> None:

        # Determine scope
        if args.scope == 'global':
            if isinstance(context.channel, discord.DMChannel):
                scope = context.channel
            else:
                scope = context.channel.guild
        elif args.scope == 'channel':
            if isinstance(context.channel, discord.DMChannel):
                await utils.send_split('`channel` scope not available in a DM. Use `global` instead.', context.channel)
                return
            scope = context.channel
        else:
            await utils.send_split('`<scope>` must be one of: global, channel', context.channel)
            return

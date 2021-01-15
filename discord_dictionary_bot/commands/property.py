import io

from discord_slash import SlashContext

from .command import Command, Context
import discord
import argparse
from .. import utils
from ..properties import Properties
from ..discord_bot_client import DiscordBotClient
from contextlib import redirect_stderr


class PropertyCommand(Command):

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
            self.client.sync(slash_context.send(send_type=3, content=reply, hidden=True))

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
            self.client.sync(slash_context.send(send_type=3, content=reply, hidden=True))

        @client.slash_command_decorator.subcommand(base=self.name, subcommand_group='channel', name='list')
        async def _on_channel_list_subcommand(slash_context: SlashContext, *args):
            reply = self._get_property_list(slash_context.channel)
            self.client.sync(slash_context.send(send_type=3, content=reply, hidden=True))

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
            self.client.sync(slash_context.send(send_type=3, content=reply, hidden=True))

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
            self.client.sync(slash_context.send(send_type=3, content=reply, hidden=True))

    def execute(self, context: Context, args: tuple):
        try:
            parser = argparse.ArgumentParser()
            parser.add_argument('scope', choices=['global', 'channel'])

            subparsers = parser.add_subparsers(dest='action')
            subparsers.required = True

            # Set
            set_parser = subparsers.add_parser('set')
            set_parser.add_argument('key')
            set_parser.add_argument('value')

            # Delete
            set_parser = subparsers.add_parser('del')
            set_parser.add_argument('key')

            # Do not remove!
            list_parser = subparsers.add_parser('list')

            # Parse arguments but suppress stderr output
            stderr_stream = io.StringIO()
            with redirect_stderr(stderr_stream):
                args = parser.parse_args(args)
        except SystemExit:
            self.client.sync(utils.send_split(f'Invalid arguments!\nUsage: `{self.name} {self.usage}`', context.channel))
            return

        # Determine scope
        if args.scope == 'global':
            if isinstance(context.channel, discord.DMChannel):
                scope = context.channel
            else:
                scope = context.channel.guild
        elif args.scope == 'channel':
            if isinstance(context.channel, discord.DMChannel):
                self.client.sync(utils.send_split('`channel` scope not available in a DM. Use `global` instead.', context.channel))
                return
            scope = context.channel
        else:
            self.client.sync(utils.send_split('`<scope>` must be one of: global, channel', context.channel))
            return

        if args.action == 'list':

            reply = self._get_property_list(scope)
            self.client.sync(utils.send_split(reply, context.channel))

        elif args.action == 'set':

            reply = self._set_property(scope, args.key, args.value)
            self.client.sync(utils.send_split(reply, context.channel))

        elif args.action == 'del':

            reply = self._delete_property(scope, args.key)
            self.client.sync(utils.send_split(reply, context.channel))

    def _get_property_list(self, scope):
        reply = '__'
        if isinstance(scope, discord.Guild):
            reply += 'Server '
        elif isinstance(scope, discord.TextChannel):
            reply += 'Channel '
        reply += 'properties__\n'

        properties = self._properties.list(scope=scope)
        for k, v in properties.items():
            reply += f'{k}: `{v}`\n'

        return reply

    def _set_property(self, scope, key, value):
        if self._properties.set(scope, key, value):
            return f'Set property `{key}` to `{value}`.'
        else:
            return 'Failed to set property.'

    def _delete_property(self, scope, key):
        if isinstance(scope, discord.Guild):
            return 'Can\'t delete a global property!'

        self._properties.delete(scope, key)
        return f'Deleted property `{key}`'

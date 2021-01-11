import io
from commands import Command, Context
import discord
import argparse
import utils
from properties import Properties
from discord_bot_client import DiscordBotClient
from contextlib import redirect_stderr


class PropertyCommand(Command):

    def __init__(self, client: DiscordBotClient, properties: Properties):
        super().__init__(client, 'property', aliases=['p'], description='Change the bot\'s properties for a channel or server. Use this to change the bot prefix, default text-to-speech language, etc.',
                         usage='<scope> (list | set <key> <value> | del <key>)')
        self._properties = properties

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
            reply = '__'
            if args.scope == 'global':
                reply += 'Server '
            elif args.scope == 'channel':
                reply += 'Channel '
            reply += 'properties__\n'

            properties = self._properties.list(scope=scope)
            for k, v in properties.items():
                reply += f'{k}: `{v}`\n'
            self.client.sync(utils.send_split(reply, context.channel))
        elif args.action == 'set':

            # Set property
            if self._properties.set(scope, args.key, args.value):
                self.client.sync(utils.send_split('Property set.', context.channel))
            else:
                self.client.sync(utils.send_split('Failed to set property.', context.channel))

        elif args.action == 'del':

            # Make sure scope is not global
            if args.scope == 'global':
                self.client.sync(utils.send_split('Can\'t delete a global property!', context.channel))
                return

            self._properties.delete(scope, args.key)
            self.client.sync(utils.send_split('Property removed.', context.channel))

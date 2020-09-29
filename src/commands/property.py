from commands.command import Command
import discord
import argparse
import utils
from properties import Properties


class PropertyCommand(Command):

    def __init__(self, client: discord.Client, properties: Properties):
        super().__init__(client, 'property', aliases=['p'], description='Sets the specified property.', usage='<scope> (list | set <key> <value> | del <key>)')
        self._properties = properties

    def execute(self, message: discord.Message, args: tuple):
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

            list_parser = subparsers.add_parser('list')

            args = parser.parse_args(args)
        except SystemExit:
            self.client.sync(utils.send_split(f'Invalid arguments!\nUsage: `{self.name} {self.usage}`', message.channel))
            return

        # Determine scope
        if args.scope == 'global':
            scope = message.guild
        elif args.scope == 'channel':
            scope = message.channel
        else:
            self.client.sync(utils.send_split('`<scope>` must be one of: global, channel', message.channel))
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
            self.client.sync(utils.send_split(reply, message.channel))
        elif args.action == 'set':

            # Set property
            if self._properties.set(scope, args.key, args.value):
                self.client.sync(utils.send_split('Property set.', message.channel))
            else:
                self.client.sync(utils.send_split('Failed to set property.', message.channel))

        elif args.action == 'del':

            # Make sure scope is not global
            if args.scope == 'global':
                self.client.sync(utils.send_split('Can\'t delete a global property!', message.channel))
                return

            self._properties.delete(scope, args.key)
            self.client.sync(utils.send_split('Property removed.', message.channel))

import discord
from discord.ext import commands
from properties import FirestorePropertyManager, Property
from typing import Any, Union


class Preferences(commands.Cog, name='preferences'):

    def __init__(self):

        self._scoped_property_manager = FirestorePropertyManager([
            Property('prefix', default='.'),
            Property('text_to_speech', choices=['force', 'flag', 'disable'], default='flag'),
            Property('language', default='en-us-wavenet-c')
        ])

    @property
    def scoped_property_manager(self):
        return self._scoped_property_manager

    @commands.group(
        name='property',
        aliases=['p'],
        help='Change the bot\'s properties for a channel or server. Use this to change the bot prefix, default text-to-speech language, etc.'
    )
    async def property(self, context):
        if context.invoked_subcommand is None:
            raise commands.errors.ArgumentParsingError()

    @property.command(name='set')
    async def set(self, context, scope_name: str, key: str, value: str):
        scope = self._get_scope_from_name(scope_name, context)
        if scope is None:
            await context.send(f'Invalid scope: `{scope_name}`! Must be either `guild` or `channel`.')
            return

        self._scoped_property_manager.set(key, value, scope)
        await context.send(f'Successfully set `{key}` to `{value}` in `{scope_name}`.')

    @property.command(name='list')
    async def list(self, context: commands.Context, scope_name: str = 'all'):
        if scope_name == 'all':

            for scope_name in ('guild', 'channel'):
                scope = self._get_scope_from_name(scope_name, context)
                if scope is not None:
                    properties = self._scoped_property_manager.get_all(scope)
                    if len(properties) > 0:
                        await context.send(self._print_properties(properties, scope))

        else:

            scope = self._get_scope_from_name(scope_name, context)
            if scope is None:
                await context.send(f'Invalid scope: `{scope_name}`! Must be either `guild` or `channel`.')
                return

            properties = self._scoped_property_manager.get_all(scope)
            await context.send(self._print_properties(properties, scope))

    @property.command(name='remove')
    async def remove(self, context: commands.Context, scope_name: str, key: str):
        scope = self._get_scope_from_name(scope_name, context)
        if scope is None:
            await context.send(f'Invalid scope: `{scope_name}`! Must be either `guild` or `channel`.')
            return
        elif scope_name == 'guild':
            await context.send(f'Guild properties cannot be removed!')
            return

        self._scoped_property_manager.remove(key, scope)
        await context.send(f'Successfully removed `{key}` from `{scope_name}`.')

    @staticmethod
    def _get_scope_from_name(scope_name: str, context: commands.Context):
        try:
            if scope_name == 'channel':
                return context.channel
            elif scope_name == 'guild':
                return context.channel.guild
        except AttributeError:
            return None
        return None

    @staticmethod
    def _print_properties(properties: {str, Any}, scope: Union[discord.Guild, discord.TextChannel, discord.DMChannel]) -> str:
        reply = '__'
        if isinstance(scope, discord.Guild):
            reply += 'Server'
        elif isinstance(scope, discord.TextChannel):
            reply += 'Channel'
        elif isinstance(scope, discord.DMChannel):
            reply += 'DM Channel'
        else:
            reply += f'Scope'
        reply += ' properties__\n'

        for k, v in properties.items():
            reply += f'{k}: `{v}`\n'

        if len(properties) == 0:
            reply += 'No properties set'

        return reply

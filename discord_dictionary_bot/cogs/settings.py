import discord
from discord_slash import SlashContext, cog_ext
from discord.ext import commands
from ..property_manager import FirestorePropertyManager, Property, InvalidKeyError, InvalidValueError, BooleanProperty, ListProperty
from typing import Any, Union, Optional
from ..utils import send_maybe_hidden


class Settings(commands.Cog):
    PROPERTY_COMMAND_DESCRIPTION = 'Change the bot\'s properties for a channel or server. Use this to change the bot prefix, default text-to-speech language, etc.'
    PROPERTY_NAME_OPTION = {
        'name': 'name',
        'description': 'Property name.',
        'type': 3,
        'required': True,
        'choices': [
            {
                'name': 'text_to_speech',
                'value': 'text_to_speech'
            },
            {
                'name': 'language',
                'value': 'language'
            },
            {
                'name': 'prefix',
                'value': 'prefix'
            }
        ]
    }

    def __init__(self):
        self._scoped_property_manager = FirestorePropertyManager([
            Property(
                'prefix',
                default='.',
                description='The bot\'s prefix.'
            ),
            Property(
                'text_to_speech',
                choices=['force', 'flag', 'disable'],
                default='flag',
                description='force: All definition requests will use text-to-speech. flag: You must use the flag to use text-to-speech. disable: Text-to-speech is disabled.'
            ),
            Property(
                'language',
                default='en-us-wavenet-c',
                description='The language to use when displaying definitions and speaking.'
            ),
            BooleanProperty(
                'show_definition_source',
                default=False,
                description='If enabled, the bot will show the definition source at the end of each definition.'
            ),
            ListProperty(
                'dictionary_apis',
                default=['unofficial_google', 'owlbot', 'merriam_webster_collegiate', 'merriam_webster_medical', 'rapid_words'],
                choices=['owlbot', 'unofficial_google', 'merriam_webster_medical', 'merriam_webster_collegiate', 'rapid_words'],
                description='A list of dictionary APIs to use in order of preference.'
            )
        ])

    @property
    def scoped_property_manager(self):
        return self._scoped_property_manager

    @commands.group(
        name='settings',
        aliases=['p'],
        help=PROPERTY_COMMAND_DESCRIPTION,
        usage='(list <scope> | set <scope> <name> <value> | remove <scope> <name>)'
    )
    async def property(self, context):
        if context.invoked_subcommand is None:
            raise commands.errors.ArgumentParsingError()

    @property.command(name='set')
    async def set(self, context, scope_name: str, key: str, value: str):
        await self._set(context, scope_name, key, value)

    @cog_ext.cog_subcommand(
        base='settings',
        name='set',
        description='Set a property.',
        options=[
            {
                'name': 'scope',
                'description': 'Property scope.',
                'type': 3,
                'required': True,
                'choices': [
                    {
                        'name': 'guild',
                        'value': 'guild'
                    },
                    {
                        'name': 'channel',
                        'value': 'channel'
                    }
                ]
            },
            PROPERTY_NAME_OPTION,
            {
                'name': 'value',
                'description': 'Property value.',
                'type': 3,
                'required': True
            }
        ]
    )
    async def slash_set(self, context: SlashContext, scope_name: str, key: str, value: str):
        await self._set(context, scope_name, key, value)

    async def _set(self, context: Union[commands.Context, SlashContext], scope_name: str, key: str, value: str):
        scope = self._get_scope_from_name(scope_name, context)
        if scope is None:
            if isinstance(context, SlashContext):
                await context.defer(hidden=True)
            await send_maybe_hidden(context, f'Invalid scope: `{scope_name}`! Must be either `guild` or `channel`.')
            return

        try:
            self._scoped_property_manager.set(key, value, scope)
            if isinstance(context, SlashContext):
                await context.defer()
            await context.send(f'Successfully set `{key}` to `{value}` in `{scope_name}`.')
        except InvalidKeyError as e:
            if isinstance(context, SlashContext):
                await context.defer(hidden=True)
            await send_maybe_hidden(context, f'Invalid key `{e.key}`')
        except InvalidValueError as e:
            if isinstance(context, SlashContext):
                await context.defer(hidden=True)
            await send_maybe_hidden(context, f'Invalid value `{e.value}` for key `{e.key}`.')

    @property.command(name='list')
    async def list(self, context: commands.Context, scope_name: Optional[str] = 'all'):
        await self._list(context, scope_name)

    @cog_ext.cog_subcommand(
        base='settings',
        name='list',
        description='Shows a list of guild or server settings.',
        options=[
            {
                'name': 'scope',
                'description': 'Property scope.',
                'type': 3,
                'choices': [
                    {
                        'name': 'all',
                        'value': 'all'
                    },
                    {
                        'name': 'guild',
                        'value': 'guild'
                    },
                    {
                        'name': 'channel',
                        'value': 'channel'
                    }
                ]
            }
        ]
    )
    async def slash_list(self, context: SlashContext, scope_name: Optional[str] = 'all'):
        await context.defer(hidden=True)
        await self._list(context, scope_name)

    def get_all(self, scope):
        properties = {}
        for p in self._scoped_property_manager.properties:
            if isinstance(scope, (discord.Guild, discord.DMChannel)):
                properties[p] = self._scoped_property_manager.get(p.key, scope)
            elif isinstance(scope, discord.TextChannel):
                value = self._scoped_property_manager.get(p.key, scope, recursive=False)
                if value is not None:
                    properties[p] = value
        return properties

    async def _list(self, context: Union[commands.Context, SlashContext], scope_name: str = 'all'):
        if scope_name == 'all':

            reply = ''
            for scope_name in ('guild', 'channel'):
                scope = self._get_scope_from_name(scope_name, context)
                if scope is not None:
                    properties = self.get_all(scope)
                    if len(properties) > 0:
                        reply += '\n' + self._print_properties(properties, scope)

            await send_maybe_hidden(context, reply)

        else:

            scope = self._get_scope_from_name(scope_name, context)
            if scope is None:
                await send_maybe_hidden(context, f'Invalid scope: `{scope_name}`! Must be either `guild` or `channel`.')
                return

            properties = self.get_all(scope)
            await send_maybe_hidden(context, self._print_properties(properties, scope))

    @property.command(name='remove')
    async def remove(self, context: commands.Context, scope_name: str, key: str):
        await self._remove(context, scope_name, key)

    @cog_ext.cog_subcommand(
        base='settings',
        name='remove',
        description='Remove a channel property.',
        options=[
            PROPERTY_NAME_OPTION
        ]
    )
    async def slash_remove(self, context: SlashContext, key: str):
        await self._remove(context, 'channel', key)

    async def _remove(self, context: Union[commands.Context, SlashContext], scope_name: str, key: str):
        scope = self._get_scope_from_name(scope_name, context)
        if scope is None:
            if isinstance(context, SlashContext):
                await context.defer(hidden=True)
            await send_maybe_hidden(context, f'Invalid scope: `{scope_name}`! Must be either `guild` or `channel`.')
            return

        try:
            self._scoped_property_manager.remove(key, scope)
        except InvalidKeyError:
            await send_maybe_hidden(context, 'Invalid property name!')
            return

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
    def _print_properties(properties: {Property: Any}, scope: Union[discord.Guild, discord.TextChannel, discord.DMChannel]) -> str:
        reply = ''
        if isinstance(scope, discord.Guild):
            reply += '__**Server Settings**__\n'
            reply += 'These settings affect every channel in your server, unless they are overridden with a channel-specific setting.\n\n'
        elif isinstance(scope, discord.TextChannel):
            reply += '__**Channel Settings**__\n'
            reply += 'These settings only affect this channel and take priority over server settings.\n\n'
        elif isinstance(scope, discord.DMChannel):
            reply += '__**DM Settings**__\n'

        for p in sorted(properties, key=lambda x: x.key):
            reply += f'**{p.key}**: `{p.to_string(properties[p])}`\n'

        if len(properties) == 0:
            reply += 'No properties set'

        return reply

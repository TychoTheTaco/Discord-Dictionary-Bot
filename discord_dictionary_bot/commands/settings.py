from typing import Any, Union, Literal

import discord
from discord import app_commands

from ..property_manager import Property, InvalidKeyError, InvalidValueError, ScopedPropertyManager


ScopeNameType = Literal['all', 'guild', 'channel']
PropertyKeyType = Literal['text_to_speech', 'language', 'prefix', 'show_definition_source', 'dictionary_apis', 'auto_translate']


class Settings(app_commands.Group):
    PROPERTY_COMMAND_DESCRIPTION = 'Change the bot\'s properties for a channel or server. Use this to change the bot prefix, default text-to-speech language, etc.'

    def __init__(self, property_manager: ScopedPropertyManager):
        super().__init__()
        self._scoped_property_manager = property_manager

    @property
    def scoped_property_manager(self):
        return self._scoped_property_manager

    @app_commands.command(name='set', description='Set a setting.')
    @app_commands.describe(key='Property name', value='Property value')
    async def set(self, interaction: discord.Interaction, scope_name: Literal['guild', 'channel'], key: PropertyKeyType, value: str):

        scope = self._get_scope_from_name(scope_name, interaction)
        if scope is None:
            await interaction.response.send_message(f'Invalid scope: `{scope_name}`! Must be either `guild` or `channel`.', ephemeral=True)
            return

        try:
            self._scoped_property_manager.set(key, value, scope)
            await interaction.response.send_message(f'Successfully set `{key}` to `{value}` in `{scope_name}`.')
        except InvalidKeyError as e:
            await interaction.response.send_message(f'Invalid key `{e.key}`', ephemeral=True)
        except InvalidValueError as e:
            await interaction.response.send_message(f'Invalid value `{e.value}` for key `{e.key}`.', ephemeral=True)

    @app_commands.command(name='list', description='Shows a list of guild or server settings.')
    async def list(self, interaction: discord.Interaction, scope_name: ScopeNameType = 'all'):
        if scope_name == 'all':

            reply = ''
            for scope_name in ('guild', 'channel'):
                scope = self._get_scope_from_name(scope_name, interaction)
                if scope is not None:
                    properties = self.get_all(scope)
                    if len(properties) > 0:
                        reply += '\n' + self._print_properties(properties, scope)

            await interaction.response.send_message(reply, ephemeral=True)

        else:

            scope = self._get_scope_from_name(scope_name, interaction)
            if scope is None:
                await interaction.response.send_message(f'Invalid scope: `{scope_name}`! Must be either `guild` or `channel`.', ephemeral=True)
                return

            properties = self.get_all(scope)
            await interaction.response.send_message(self._print_properties(properties, scope), ephemeral=True)

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

    @app_commands.command(name='remove', description='Remove something')
    @app_commands.describe(key='Property name')
    async def remove(self, interaction: discord.Interaction, scope_name: Literal['guild', 'channel'], key: PropertyKeyType):

        scope = self._get_scope_from_name(scope_name, interaction)
        if scope is None:
            await interaction.response.send_message(f'Invalid scope: `{scope_name}`! Must be either `guild` or `channel`.', ephemeral=True)
            return

        try:
            self._scoped_property_manager.remove(key, scope)
        except InvalidKeyError:
            await interaction.response.send_message('Invalid property name!', ephemeral=True)
            return

        await interaction.response.send_message(f'Successfully removed `{key}` from `{scope_name}`.')

    @staticmethod
    def _get_scope_from_name(scope_name: str, interaction: discord.Interaction):
        try:
            if scope_name == 'channel':
                return interaction.channel
            elif scope_name == 'guild':
                return interaction.guild
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

        reply += 'Use `help settings` to see more info about settings.\n\n'

        for p in sorted(properties, key=lambda x: x.key):
            reply += f'**{p.key}**: `{p.to_string(properties[p])}`\n'

        if len(properties) == 0:
            reply += 'No properties set'

        return reply

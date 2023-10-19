import datetime
import logging
import sys
from pathlib import Path
from typing import Union, Any, Optional, Sequence

import discord.ext.commands
from discord import Message, Guild, Interaction
from discord.abc import Snowflake
from discord.app_commands import ContextMenu, Command
from discord.ext.commands import Cog
from discord.ext.commands.bot import Bot
from google.cloud import firestore

from .analytics import log_command, log_context_menu_usage
from .cogs import Settings, Dictionary, Statistics
from .dictionary_api import DictionaryAPI
from .property_manager import FirestorePropertyManager, Property, BooleanProperty, ListProperty
from .utils import get_bot_permissions

# Set up logging
logger = logging.getLogger(__name__)


def interaction_data_to_string(data):
    if isinstance(data, list):

        if 'value' not in data[0]:
            return interaction_data_to_string(data[0])
        else:
            result = {}
            for d in data:
                result[d['name']] = d['value']
            return f'{result}'

    name = data['name']

    options = data.get('options')
    if options:
        return name + ' ' + interaction_data_to_string(options)

    return name


class DiscordBotClient(Bot):

    def __init__(self, dictionary_apis: [DictionaryAPI], ffmpeg_path: Union[str, Path], **kwargs):
        """
        Creates a new Discord bot client.
        :param dictionary_apis: A list of dictionary APIs that are available for the bot to use.
        :param ffmpeg_path: Path to ffmpeg executable.
        :param kwargs:
        """
        super().__init__('', help_command=None, intents=discord.Intents.default(), **kwargs)
        self._dictionary_apis = dictionary_apis
        self._ffmpeg_path = ffmpeg_path
        self._scoped_property_manager = FirestorePropertyManager([
            Property(
                'text_to_speech',
                choices=['force', 'flag', 'disable'],
                default='flag',
                description='Choices:\n'
                            '`force`: All definition requests will use text-to-speech.\n'
                            '`flag`: You must use the flag to use text-to-speech.\n'
                            '`disable`: Text-to-speech is disabled.'
            ),
            Property(
                'language',
                default='en',
                description='The language to use when displaying definitions and speaking. This can be a two-letter language code or a language name.'
            ),
            BooleanProperty(
                'show_definition_source',
                default=False,
                description='Choices:\n'
                            '`true`: The bot will show the definition source at the end of each definition.\n'
                            '`false`: The bot will not show the definition source.'
            ),
            ListProperty(
                'dictionary_apis',
                default=['unofficial_google', 'owlbot', 'merriam_webster_collegiate', 'merriam_webster_medical', 'rapid_words'],
                choices=['owlbot', 'unofficial_google', 'merriam_webster_medical', 'merriam_webster_collegiate', 'rapid_words'],
                description='A comma-separated list of dictionary APIs to use in order of preference.\n'
                            'Choices:\n'
                            '`unofficial_google`, `owlbot`, `merriam_webster_collegiate`, `merriam_webster_medical`, `rapid_words`'
            ),
            BooleanProperty(
                'auto_translate',
                default=False,
                description='Choices:\n'
                            '`true`: Automatically translate words before looking up their definition.\n'
                            '`false`: Don\'t translate words before looking up their definition.'
            )
        ])

    async def setup_hook(self) -> None:
        guild_ids = []

        async def add_cog_wrapper(cog: Cog, guilds: Optional[Sequence[Snowflake]] = None):
            if not guilds:
                guilds = []
            guild_ids.extend(guilds)
            await self.add_cog(cog, guilds=guilds)

        # Add cogs
        await add_cog_wrapper(Dictionary(self, self._dictionary_apis, self._ffmpeg_path))
        await add_cog_wrapper(Settings(self._scoped_property_manager))
        await add_cog_wrapper(Statistics(self), guilds=[discord.Object(id='799455809297842177'), discord.Object(id='454852632528420876')])

        # Sync slash commands
        await self.tree.sync()
        for guild in guild_ids:
            try:
                await self.tree.sync(guild=guild)
            except discord.errors.Forbidden:
                # If the bot isn't in the guild, we will get a Forbidden error
                logger.warning(f'Failed to sync commands for guild {guild.id}')

    async def on_app_command_completion(self, interaction: Interaction, command: Union[Command, ContextMenu]):
        if isinstance(command, Command):
            logger.info(f'[G: "{interaction.guild}", C: "{interaction.channel}"] "/{interaction_data_to_string(interaction.data)}"')
            log_command(command.name, interaction)
        elif isinstance(command, ContextMenu):
            logger.info(f'[G: "{interaction.guild}", C: "{interaction.channel}"] "CM -> {command.name}"')
            log_context_menu_usage(command.name, interaction)
        else:
            logger.error('Unknown command type!')

    async def on_ready(self):
        logger.info(f'Logged on as {self.user}!')

        # Check for new guilds
        firestore_client = firestore.Client()
        for guild in self.guilds:
            document = firestore_client.collection('guilds').document(str(guild.id))
            snapshot = document.get()
            if not snapshot.exists:
                await self.on_guild_join(guild)

    async def on_guild_join(self, guild: Guild):
        logger.info('Joined guild: ' + guild.name)

        firestore_client = firestore.Client()
        guild_document = firestore_client.collection('guilds').document(str(guild.id))
        snapshot = guild_document.get()

        if not snapshot.exists:
            guild_document.set({
                'joined': datetime.datetime.now()
            })

    async def on_error(self, event_method: str, /, *args: Any, **kwargs: Any) -> None:
        exception = sys.exc_info()[1]
        if isinstance(exception, discord.errors.Forbidden):
            if event_method == 'on_message':
                message: Message = args[0]
                logger.error(f'Missing permissions. We have {get_bot_permissions(message.channel)}')
                return
        await super().on_error(event_method, *args, **kwargs)

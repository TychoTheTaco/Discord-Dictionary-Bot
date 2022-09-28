import datetime
import logging
import sys
from pathlib import Path
from typing import Union, Any

import discord.ext.commands
from discord import Message, Guild, Interaction
from discord.app_commands import ContextMenu, Command
from discord.ext.commands.bot import Bot
from google.cloud import firestore

# from .analytics import log_command
from .commands import Settings, Dictionary, Statistics
from .dictionary_api import DictionaryAPI
from .property_manager import FirestorePropertyManager, Property, BooleanProperty, ListProperty
from .utils import get_bot_permissions

# Set up logging
logger = logging.getLogger(__name__)


def get_prefix(bot: Bot, message: Message):
    return bot._scoped_property_manager.get('prefix', message.channel)


class DiscordBotClient(Bot):

    def __init__(self, dictionary_apis: [DictionaryAPI], ffmpeg_path: Union[str, Path], **kwargs):
        """
        Creates a new Discord bot client.
        :param dictionary_apis: A list of 'DictionaryAPI's that are available for the bot to use.
        :param ffmpeg_path:
        :param kwargs:
        """
        super().__init__(get_prefix, help_command=None, intents=discord.Intents.default(), **kwargs)

        self._scoped_property_manager = FirestorePropertyManager([
            Property(
                'prefix',
                default='.',
                description='The bot\'s prefix. This can be one or more characters. If you forget the prefix, just mention the bot and it will show you the current prefix.'
            ),
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

        self.tree.add_command(Dictionary(self, dictionary_apis, ffmpeg_path), guild=discord.Object(id='799455809297842177'))
        self.tree.add_command(Settings(self._scoped_property_manager), guild=discord.Object(id='799455809297842177'))
        self.tree.add_command(Statistics(self), guild=discord.Object(id='799455809297842177'))

    async def on_app_command_completion(self, interaction: Interaction, command: Union[Command, ContextMenu]):
        args = {option['name']: option['value'] for option in interaction.data['options'][0]['options']}
        logger.info(f'[G: "{interaction.guild}", C: "{interaction.channel}"] "/{command.name}" {args}')

    async def on_ready(self):
        logger.info(f'Logged on as {self.user}!')

        await self.tree.sync(guild=discord.Object(id='799455809297842177'))

        # Check for new guilds
        firestore_client = firestore.Client()
        for guild in self.guilds:
            document = firestore_client.collection('guilds').document(str(guild.id))
            snapshot = document.get()
            if not snapshot.exists:
                await self.on_guild_join(guild)

    async def on_message(self, message: Message):

        # If we are mentioned, show our prefix and help
        if self.user in message.mentions:
            prefix = get_prefix(self, message)
            await message.reply(f'My prefix here is `{prefix}`\nUse `{prefix}help` to view available commands.', mention_author=False)

        await super().on_message(message)

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


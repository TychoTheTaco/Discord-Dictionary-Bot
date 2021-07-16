import logging
from pathlib import Path
from typing import Union

from discord import Message
from discord.ext.commands.bot import Bot

from .cogs import Help, Preferences, Dictionary, Statistics
from .dictionary_api import DictionaryAPI
from discord.ext import commands
from discord_slash import SlashCommand, SlashContext
from .analytics import log_command

# Set up logging
logger = logging.getLogger(__name__)


def get_prefix(bot: Bot, message: Message):
    preferences_cog = bot.get_cog('Preferences')
    return preferences_cog.scoped_property_manager.get('prefix', message.channel)


class DiscordBotClient(Bot):

    def __init__(self, dictionary_apis: [DictionaryAPI], ffmpeg_path: Union[str, Path], **kwargs):
        """
        Creates a new Discord bot client.
        :param dictionary_apis: A list of 'DictionaryAPI's that are available for the bot to use.
        :param ffmpeg_path:
        :param kwargs:
        """
        super().__init__(get_prefix, help_command=None, **kwargs)
        slash = SlashCommand(self, sync_commands=True)  # This needs to be here for slash commands to work!
        self.add_cog(Help())
        self.add_cog(Dictionary(self, dictionary_apis, ffmpeg_path))
        self.add_cog(Preferences())
        self.add_cog(Statistics(self))

        @self.before_invoke
        async def before_command_invoked(context: commands.Context):
            logger.info(f'[G: "{context.guild}", C: "{context.channel}"] "{context.message.content}"')
            log_command(context.command.name, False, context)

        @self.event
        async def on_slash_command(context: SlashContext):
            logger.info(f'[G: "{context.guild}", C: "{context.channel}"] "/{context.command}" {context.kwargs}')
            log_command(context.command, True, context)

    async def on_command_error(self, context: commands.Context, exception):
        if isinstance(exception, commands.errors.CommandNotFound):
            pass  # Ignore command not found
        elif isinstance(exception, commands.errors.MissingRequiredArgument):
            await context.send('Invalid command usage!')
        elif isinstance(exception, commands.errors.ArgumentParsingError):
            await context.send('Invalid arguments!')
        else:
            logger.error('Error on command!', exc_info=exception)
            await super().on_command_error(context, exception)

    async def on_ready(self):
        logger.info(f'Logged on as {self.user}!')

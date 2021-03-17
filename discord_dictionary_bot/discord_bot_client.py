import logging
from pathlib import Path
from typing import Union

from discord import Message
from discord.ext.commands.bot import Bot

from cogs import Help, Preferences, Dictionary, Statistics
from dictionary_api import DictionaryAPI
from discord.ext import commands
from discord_slash import SlashCommand

# Set up logging
logger = logging.getLogger(__name__)


def get_prefix(bot: Bot, message: Message):
    preferences_cog = bot.get_cog('Preferences')
    return preferences_cog.scoped_property_manager.get('prefix', message.channel)


class DiscordBotClient(Bot):

    def __init__(self, dictionary_api: DictionaryAPI, ffmpeg_path: Union[str, Path], **kwargs):
        super().__init__(get_prefix, help_command=None, **kwargs)
        slash = SlashCommand(self, sync_commands=True)
        self.add_cog(Help())
        self.add_cog(Dictionary(self, dictionary_api, ffmpeg_path))
        self.add_cog(Preferences())
        self.add_cog(Statistics(self))

    async def on_command_error(self, context: commands.Context, exception):
        if isinstance(exception, commands.errors.MissingRequiredArgument):
            await context.send('Invalid command usage!')
        elif isinstance(exception, commands.errors.ArgumentParsingError):
            await context.send('Invalid arguments!')
        else:
            logger.error('Error on command!', exc_info=exception)
            await super().on_command_error(context, exception)

    async def on_ready(self):
        logger.info(f'Logged on as {self.user}!')

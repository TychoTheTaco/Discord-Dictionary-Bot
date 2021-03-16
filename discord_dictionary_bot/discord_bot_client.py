import logging
from pathlib import Path
from typing import Union

from discord import Message
from discord.ext.commands.bot import Bot

from cogs import dictionary, preferences, misc
from dictionary_api import DictionaryAPI
from discord.ext import commands
from discord_slash import SlashCommand

# Set up logging
logger = logging.getLogger(__name__)


class DiscordBotClient(Bot):

    def __init__(self, dictionary_api: DictionaryAPI, ffmpeg_path: Union[str, Path], **kwargs):
        super().__init__(DiscordBotClient.gp, **kwargs)
        slash = SlashCommand(self, override_type=True)
        self.add_cog(dictionary.Dictionary(self, dictionary_api, ffmpeg_path))
        self.add_cog(preferences.Preferences())
        self.add_cog(misc.Miscellaneous(self))

    async def on_command_error(self, context: commands.Context, exception):
        if isinstance(exception, commands.errors.MissingRequiredArgument):
            await context.send('Invalid command usage!')
        elif isinstance(exception, commands.errors.ArgumentParsingError):
            await context.send('Invalid arguments!')
        return await super().on_command_error(context, exception)

    @staticmethod
    def gp(bot: Bot, message: Message) -> str:
        """
        Get this bot's summon prefix for the specified text channel. It will usually be the same for all channels in a server but may vary between servers.
        :param channel: The text channel.
        :return: The summon prefix.
        """
        #return self._properties.get(channel, 'prefix')
        return '.'



    #async def on_ready(self):
    #    logger.info(f'Logged on as {self.user}!')

from abc import ABC, abstractmethod

import discord
from discord_slash import SlashContext

from discord_dictionary_bot.discord_bot_client import DiscordBotClient


class Context:
    """
    This is passed to each command's 'execute' function so that they are aware of the context in which they are executing.
    """

    def __init__(self, author: discord.User, channel: discord.abc.Messageable, slash_context: SlashContext = None):
        self._author = author
        self._channel = channel
        self._slash_context = slash_context

    @property
    def author(self):
        return self._author

    @property
    def channel(self):
        return self._channel

    @property
    def slash_context(self):
        return self._slash_context


class Command(ABC):

    def __init__(self, client: DiscordBotClient, name, aliases=None, description='', usage='', secret=False, slash_command_options=None):
        """
        This is the base class for commands.
        :param client: The client this command is attached to.
        :param name: The name of this command. This is the name the bot will react to.
        :param aliases: Aliases that the bot will also react to for this command.
        :param description: A description of the command that shows up in the help message.
        :param usage: A usage description that shows up in the help message.
        :param secret: If this command is secret, it will not show up in the help message.
        """
        self._client = client
        self._name = name
        self._aliases = [] if aliases is None else aliases
        self._description = description
        self._usage = usage
        self._secret = secret

        # Set up slash command support
        if slash_command_options is not None:

            # If the command options contain a subcommand, they will each need their own decorator. This case needs to be handled manually by the subclass.
            if any(x['type'] < 3 for x in slash_command_options):
                return

            # Note: discord_slash currently doesn't support keyword arguments or default arguments so 'args' may contain values in the wrong position when some optional arguments are not given. Therefore, each 'Command' subclass needs to
            # validate the arguments based on their type. If the arguments are the same type, there is unfortunately no good way to differentiate them since all we get here is a tuple.
            @client.slash_command_decorator.slash(name=name, options=slash_command_options)
            async def _on_slash_command(slash_context, *args):
                await self.execute_slash_command(slash_context, args)

    @property
    def client(self) -> DiscordBotClient:
        return self._client

    @property
    def name(self) -> str:
        return self._name

    @property
    def aliases(self) -> [str]:
        return self._aliases

    @property
    def description(self) -> str:
        return self._description

    @property
    def usage(self) -> str:
        return self._usage

    @property
    def secret(self) -> bool:
        return self._secret

    @abstractmethod
    async def execute(self, context: Context, args: tuple) -> None:
        pass

    async def execute_slash_command(self, slash_context: SlashContext, args: tuple) -> None:
        pass

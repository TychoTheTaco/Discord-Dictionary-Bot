from abc import ABC, abstractmethod
import discord

import discord_bot_client


class Command(ABC):

    def __init__(self, client: 'discord_bot_client.DiscordBotClient', name, aliases=None, description='', usage='', secret=False):
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

    @property
    def client(self) -> 'discord_bot_client.DiscordBotClient':
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

    def matches(self, string) -> bool:
        return string in [self._name] + self._aliases

    @abstractmethod
    def execute(self, message: discord.Message, args: tuple) -> None:
        pass

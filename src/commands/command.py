from abc import ABC, abstractmethod
import discord


class Command(ABC):

    def __init__(self, name, aliases=None, description='', usage=''):
        self._name = name
        self._aliases = [] if aliases is None else aliases
        self._description = description
        self._usage = usage

    @property
    def name(self):
        return self._name

    @property
    def aliases(self):
        return self._aliases

    @property
    def description(self):
        return self._description

    @property
    def usage(self):
        return self._usage

    def matches(self, string):
        return string in [self._name] + self._aliases

    @abstractmethod
    def execute(self, client: discord.client, message: discord.Message, args: tuple):
        """
        Execute this command with the specified arguments.
        :param client: The discord client that this command is executing in.
        :param message: The message that triggered this command.
        :param args: Arguments for this command.
        :return:
        """
        pass

import discord
from typing import Union


class Properties:

    def __init__(self):
        """
        Properties:
            prefix:
                bot prefix.
            textToSpeech:
                force: Force text to speech enabled even without the flag set on individual commands
                flag: Only use text to speech when the flag is set on individual commands.
                disable: Disable all text-to-speech even if the flag is enabled on individual commands.
            language:
                sets the default language to be used for text-to-speech when no language flag is given.
        """
        self._properties = {}

    def get_defaults(self):
        return {
            'prefix': '.',
            'text_to_speech': 'flag',
            'language': 'en-us'
        }

    def set(self, scope, key, value):
        self._get_scope(scope)[key] = value
        self.save()

    def get(self, scope: Union[discord.Guild, discord.TextChannel], key) -> str:
        return self._get_scope(scope)[key]

    def list(self, scope):
        return self._get_scope(scope)

    def _get_scope(self, scope: Union[discord.Guild, discord.TextChannel]) -> dict:
        if type(scope) is discord.Guild:
            if scope not in self._properties:
                self._properties[scope] = self.get_defaults()
        elif type(scope) is discord.TextChannel:
            if scope not in self._properties:
                return self._get_scope(scope.guild)
        return self._properties[scope]

    def save(self):
        pass

    def load(self):
        pass

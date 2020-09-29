import discord
from typing import Union
from google.cloud import firestore


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
        self._firestore_client = firestore.Client()

    def get_defaults(self):
        return {
            'prefix': '.',
            'text_to_speech': 'flag',
            'language': 'en-us'
        }

    def delete(self, scope, key):
        dictionary = self._get_dict(scope)
        del dictionary[key]
        self._get_snapshot(scope).reference.set(dictionary)

    def set(self, scope, key, value):
        dictionary = self._get_dict(scope)
        dictionary[key] = value
        self._get_snapshot(scope).reference.set(dictionary)  # This could be replaced with an 'update' operation but idk what option to provide to create the document if it didn't exist

    def get(self, scope: Union[discord.Guild, discord.TextChannel], key) -> str:
        if type(scope) is discord.Guild:
            return self._get_dict(scope)[key]
        elif type(scope) is discord.TextChannel:
            dictionary = self._get_dict(scope)
            if key in dictionary:
                return dictionary[key]
            return self.get(scope.guild, key)

    def list(self, scope):
        return self._get_dict(scope)

    def _get_snapshot(self, scope: Union[discord.Guild, discord.TextChannel]) -> firestore.DocumentSnapshot:
        if type(scope) == discord.Guild:
            guild_document = self._firestore_client.collection('guilds').document(str(scope.id))
            snapshot = guild_document.get()

            # Write default preferences
            if not snapshot.exists:
                print('Preferences for', scope, 'did not exist. Setting defaults.')
                guild_document.set(self.get_defaults())
                snapshot = guild_document.get()

            return snapshot
        elif type(scope) is discord.TextChannel:
            guild_document = self._firestore_client.collection('guilds').document(str(scope.guild.id))
            channel_document = guild_document.collection('channels').document(str(scope.id))
            channel_snapshot = channel_document.get()
            return channel_snapshot

    def _get_dict(self, scope: Union[discord.Guild, discord.TextChannel]) -> dict:
        snapshot = self._get_snapshot(scope)
        if type(scope) is discord.Guild:
            return snapshot.to_dict()
        elif type(scope) is discord.TextChannel:
            if snapshot.exists:
                return snapshot.to_dict()
        return {}

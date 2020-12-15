import discord
from typing import Union
from google.cloud import firestore


class Property:

    def __init__(self, key, values=None, default=None, dtype=str):
        self._key = key
        self._values = values
        self._default = default
        self._dtype = dtype

    @property
    def key(self):
        return self._key

    @property
    def values(self):
        return self._values

    @property
    def default(self):
        return self._default

    def is_valid(self, value):
        if self._values is not None:
            return value in self._values
        return type(value) is self._dtype


class Properties:

    PROPERTIES = [
        Property('prefix', default='.'),
        Property('text_to_speech', values=['force', 'flag', 'disable'], default='flag'),
        Property('language', default='en-us')
    ]

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

    def delete(self, scope, key):
        dictionary = self._get_dict(scope)
        del dictionary[key]
        self._get_snapshot(scope).reference.set(dictionary)

    def set(self, scope, key, value) -> bool:
        # Make sure property is valid
        for p in Properties.PROPERTIES:
            if p.key == key:
                if p.is_valid(value):
                    break
                else:
                    return False
        dictionary = self._get_dict(scope)
        dictionary[key] = value
        self._get_snapshot(scope).reference.set(dictionary)  # This could be replaced with an 'update' operation but idk what option to provide to create the document if it didn't exist
        return True

    # TODO: Cache values if they are unchanged to limit firestore reads
    def get(self, scope: Union[discord.Guild, discord.TextChannel], key) -> str:
        if type(scope) is discord.Guild:
            return self._get_dict(scope)[key]
        elif type(scope) is discord.TextChannel:
            dictionary = self._get_dict(scope)
            if key in dictionary:
                return dictionary[key]
            return self.get(scope.guild, key)

    def get_channel_property(self, channel: discord.TextChannel, key: str) -> Union[str, None]:
        """
        Get a channel-specific property. This will return 'None' if the property does not exist.
        :param channel:
        :param key:
        :return:
        """
        dictionary = self._get_dict(channel)
        if key in dictionary:
            return dictionary[key]
        return None

    def list(self, scope):
        return self._get_dict(scope)

    def _get_snapshot(self, scope: Union[discord.Guild, discord.TextChannel]) -> firestore.DocumentSnapshot:
        if type(scope) == discord.Guild:
            guild_document = self._firestore_client.collection('guilds').document(str(scope.id))
            snapshot = guild_document.get()

            # Write default preferences
            if not snapshot.exists:
                print('Preferences for', scope, 'did not exist. Setting defaults.')
                guild_document.set({p.key: p.default for p in Properties.PROPERTIES})
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

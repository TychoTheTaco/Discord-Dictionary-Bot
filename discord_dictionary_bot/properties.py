import discord
from typing import Union, Any, Iterable, Optional
from google.cloud import firestore
import logging
from abc import ABC, abstractmethod

# Set up logging
logger = logging.getLogger(__name__)


class Property:

    def __init__(self, key, choices=Optional[Iterable[Any]], default=Optional[Any], dtype: Any = str):
        self._key = key
        self._choices = choices
        self._default = default
        self._dtype = dtype

    @property
    def key(self):
        return self._key

    @property
    def choices(self):
        return self._choices

    @property
    def default(self):
        return self._default

    def is_valid(self, value):
        if self._choices is not None:
            return value in self._choices
        return type(value) is self._dtype


class ScopedPropertyManager(ABC):

    def __init__(self, properties: Iterable[Property]):
        self._properties = properties

    @property
    def properties(self):
        return self._properties

    @abstractmethod
    def get(self, key: str, scope: Union[discord.Guild, discord.TextChannel, discord.DMChannel]):
        pass

    @abstractmethod
    def set(self, key: str, value: Any, scope: Union[discord.Guild, discord.TextChannel, discord.DMChannel]):
        pass

    @abstractmethod
    def get_all(self, scope: Union[discord.Guild, discord.TextChannel, discord.DMChannel]):
        pass


class FirestorePropertyManager(ScopedPropertyManager):

    def __init__(self, properties: Iterable[Property]):
        super().__init__(properties)
        self._firestore_client = firestore.Client()

    def get(self, key: str, scope: Union[discord.Guild, discord.TextChannel, discord.DMChannel]):
        pass

    def set(self, key: str, value: Any, scope: Union[discord.Guild, discord.TextChannel, discord.DMChannel]):
        # Make sure the key and value are valid
        for p in self.properties:
            if p.key == key:
                if p.is_valid(value):
                    break
                else:
                    raise RuntimeError('Invalid value!')
        else:
            raise RuntimeError('Invalid key!')

    def get_all(self, scope: Union[discord.Guild, discord.TextChannel, discord.DMChannel]):
        pass


class Properties:

    PROPERTIES = [
        Property('prefix', default='.'),
        Property('text_to_speech', choices=['force', 'flag', 'disable'], default='flag'),
        Property('language', default='en-us-wavenet-c')
    ]

    def __init__(self):
        """
        Properties:
            prefix:
                command prefix.
            textToSpeech:
                force: Force text to speech enabled even without the flag set on individual commands
                flag: Only use text to speech when the flag is set on individual commands.
                disable: Disable all text-to-speech even if the flag is enabled on individual commands.
            language:
                sets the default language to be used for text-to-speech when no language flag is given.
        """
        self._firestore_client = firestore.Client()

    def delete(self, scope: Union[discord.Guild, discord.TextChannel, discord.DMChannel], key: str) -> None:
        dictionary = self._get_dict(scope)
        del dictionary[key]
        self._get_snapshot(scope).reference.set(dictionary)

    def set(self, scope: Union[discord.Guild, discord.TextChannel, discord.DMChannel], key: str, value) -> bool:
        # Make sure property is valid
        for p in Properties.PROPERTIES:
            if p.key == key:
                if p.is_valid(value):
                    break
                else:
                    return False
        dictionary = self._get_dict(scope)
        dictionary[key] = value
        logger.info(f'Set property "{key}" to "{value}" for scope "{scope}"')
        self._get_snapshot(scope).reference.set(dictionary)  # This could be replaced with an 'update' operation but idk what option to provide to create the document if it didn't exist
        return True

    # TODO: Cache values if they are unchanged to limit firestore reads
    def get(self, scope: Union[discord.Guild, discord.TextChannel, discord.DMChannel], key: str) -> Union[str, None]:
        if isinstance(scope, (discord.Guild, discord.DMChannel)):
            d = self._get_dict(scope)
            if key not in d:
                logger.error(f'Key "{key}" not in dict "{d}" for scope {scope}')
            return self._get_dict(scope)[key]
        elif type(scope) is discord.TextChannel:
            d = self._get_dict(scope)
            if key in d:
                return d[key]

            # The text-channel did not have the requested property, maybe the guild has it
            return self.get(scope.guild, key)
        else:
            logger.error(f'Scope is not a guild or channel: {type(scope)} "{scope}"')
            return None

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

    def _get_snapshot(self, scope: Union[discord.Guild, discord.TextChannel, discord.DMChannel]) -> firestore.DocumentSnapshot:
        if isinstance(scope, discord.Guild):
            guild_document = self._firestore_client.collection('guilds').document(str(scope.id))
            snapshot = guild_document.get()

            # Write default preferences
            if not snapshot.exists:
                logger.info(f'Preferences for "{scope.name}" did not exist. Setting defaults.')
                guild_document.set({p.key: p.default for p in Properties.PROPERTIES})
                snapshot = guild_document.get()

            return snapshot
        elif isinstance(scope, discord.TextChannel):
            guild_document = self._firestore_client.collection('guilds').document(str(scope.guild.id))
            channel_document = guild_document.collection('channels').document(str(scope.id))
            channel_snapshot = channel_document.get()
            return channel_snapshot
        elif isinstance(scope, discord.DMChannel):
            guild_document = self._firestore_client.collection('dms').document(str(scope.id))
            snapshot = guild_document.get()

            # Write default preferences
            if not snapshot.exists:
                logger.info(f'Preferences for "DM with {scope.recipient.name}" did not exist. Setting defaults.')
                guild_document.set({p.key: p.default for p in Properties.PROPERTIES})
                snapshot = guild_document.get()

            return snapshot
        else:
            logger.error(f'Scope is not a guild or channel: {type(scope)} "{scope}"')

    def _get_dict(self, scope: Union[discord.Guild, discord.TextChannel, discord.DMChannel]) -> dict:
        """
        Get a dictionary of properties associated with the given scope. If the scope has no properties, an empty dictionary will be returned.
        :param scope: Either a 'discord.Guild' or a 'discord.TextChannel'.
        :return: A dictionary containing the properties of the scope.
        """
        snapshot = self._get_snapshot(scope)
        if snapshot.exists:
            return snapshot.to_dict()
        return {}

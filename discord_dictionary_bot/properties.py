import discord
from typing import Union, Any, Iterable, Optional
from google.cloud import firestore
import logging
from abc import ABC, abstractmethod

# Set up logging
logger = logging.getLogger(__name__)


class InvalidKeyError(BaseException):

    def __init__(self, key: str):
        self._key = key

    @property
    def key(self):
        return self._key


class InvalidValueError(BaseException):

    def __init__(self, key: str, value: Any):
        self._key = key
        self._value = value

    @property
    def key(self):
        return self._key

    @property
    def value(self):
        return self._value


class Property:

    def __init__(self, key, choices: Optional[Iterable[Any]] = None, default: Optional[Any] = None, dtype: Any = str):
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
    def get(self, key: str, scope: Union[discord.Guild, discord.TextChannel, discord.DMChannel]) -> Optional[Any]:
        raise NotImplementedError

    @abstractmethod
    def set(self, key: str, value: Any, scope: Union[discord.Guild, discord.TextChannel, discord.DMChannel]):
        raise NotImplementedError

    @abstractmethod
    def remove(self, key: str, scope: Union[discord.Guild, discord.TextChannel, discord.DMChannel]):
        raise NotImplementedError

    @abstractmethod
    def get_all(self, scope: Union[discord.Guild, discord.TextChannel, discord.DMChannel]) -> {str: Any}:
        raise NotImplementedError


class FirestorePropertyManager(ScopedPropertyManager):

    def __init__(self, properties: Iterable[Property]):
        super().__init__(properties)
        self._firestore_client = firestore.Client()

        # Maintain a cache so that we don't need to make too many requests to Firestore.
        self._cache = {}

        # This dictionary keeps track of which scopes are dirty and need to be fetched from Firestore next time
        self._dirty = {}

    def get(self, key: str, scope: Union[discord.Guild, discord.TextChannel, discord.DMChannel]) -> Optional[Any]:
        if isinstance(scope, (discord.Guild, discord.DMChannel)):
            d = self.get_all(scope)
            if key not in d:
                logger.error(f'Key "{key}" not in dict "{d}" for scope {scope}')
            return self.get_all(scope)[key]
        elif type(scope) is discord.TextChannel:
            d = self.get_all(scope)
            if key in d:
                return d[key]

            # The text-channel did not have the requested property, maybe the guild has it
            return self.get(key, scope.guild)
        else:
            logger.error(f'Scope is not a guild or channel: {type(scope)} "{scope}"')
            return None

    def set(self, key: str, value: Any, scope: Union[discord.Guild, discord.TextChannel, discord.DMChannel]):
        # Make sure the key and value are valid
        for p in self.properties:
            if p.key == key:
                if p.is_valid(value):
                    break
                else:
                    raise InvalidValueError(key, value)
        else:
            raise InvalidKeyError(key)

        dictionary = self.get_all(scope)
        dictionary[key] = value
        logger.info(f'Set property "{key}" to "{value}" for scope "{scope}"')
        self._get_snapshot(scope).reference.set(
            dictionary)  # This could be replaced with an 'update' operation but idk what option to provide to create the document if it didn't exist
        self._dirty[scope] = True

    def remove(self, key: str, scope: Union[discord.Guild, discord.TextChannel, discord.DMChannel]):
        dictionary = self.get_all(scope)
        if key in dictionary:
            del dictionary[key]
            self._get_snapshot(scope).reference.set(dictionary)
            self._dirty[scope] = True

    def get_all(self, scope: Union[discord.Guild, discord.TextChannel, discord.DMChannel]):
        """
        Get a dictionary of properties associated with the given scope. If the scope has no properties, an empty dictionary will be returned.
        :param scope: Either a 'discord.Guild' or a 'discord.TextChannel'.
        :return: A dictionary containing the properties of the scope.
        """
        # Check the cache
        if scope in self._cache and not self._dirty[scope]:
            return self._cache[scope]

        # The data was either not in the cache, or was in the cache but it's dirty so we need to fetch it again
        snapshot = self._get_snapshot(scope)
        if snapshot.exists:
            results = snapshot.to_dict()

            # Add to cache
            self._cache[scope] = results
            self._dirty[scope] = False

            return results

        # The document did not exist
        return {}

    def _get_snapshot(self, scope: Union[discord.Guild, discord.TextChannel, discord.DMChannel]) -> firestore.DocumentSnapshot:
        if isinstance(scope, discord.Guild):
            guild_document = self._firestore_client.collection('guilds').document(str(scope.id))
            snapshot = guild_document.get()

            # Write default preferences
            if not snapshot.exists:
                logger.info(f'Preferences for "{scope.name}" did not exist. Setting defaults.')
                guild_document.set({p.key: p.default for p in self.properties})
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
                guild_document.set({p.key: p.default for p in self.properties})
                snapshot = guild_document.get()

            return snapshot
        else:
            logger.error(f'Scope is not a guild or channel: {type(scope)} "{scope}"')

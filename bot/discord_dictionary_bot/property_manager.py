from typing import Union, Any, Iterable, Optional
import logging
from abc import ABC, abstractmethod

import discord
from google.cloud import firestore

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

    def __init__(self, key, choices: Optional[Iterable[Any]] = None, default: Optional[Any] = None, dtype: Any = str, from_string=lambda x: x, description: str = ''):
        self._key = key
        self._choices = choices
        self._default = default
        self._dtype = dtype
        self._from_string = from_string
        self._description = description

    @property
    def key(self):
        return self._key

    @property
    def choices(self):
        return self._choices

    @property
    def default(self):
        return self._default

    @property
    def description(self):
        return self._description

    def is_valid(self, value):
        if self._choices is not None:
            return value in self._choices
        return type(value) is self._dtype

    def parse(self, string: str):
        return self._from_string(string)

    def to_string(self, value) -> str:
        return str(value)


class BooleanProperty(Property):

    def __init__(self, key, default: bool = False, description: str = ''):
        super().__init__(key, [True, False], default, bool, description=description)

    def parse(self, string: str):
        if string.lower() in ('true', 'false'):
            return string.lower() == 'true'
        raise InvalidValueError(self.key, string)

    def to_string(self, value) -> str:
        if value:
            return 'true'
        return 'false'


class ListProperty(Property):

    def __init__(self, key, choices: Optional[Iterable[Any]] = None, default: Optional[Any] = None, description: str = ''):
        super().__init__(key, choices, default, list, description=description)

    def parse(self, string: str):
        return string.split(',')

    def is_valid(self, value):
        for item in value:
            if item not in self.choices:
                return False
        return True

    def to_string(self, value) -> str:
        result = ''
        for i, x in enumerate(value):
            result += f'{x}'
            if i + 1 < len(value):
                result += ','
        return result + ''


class ScopedPropertyManager(ABC):

    def __init__(self, properties: Iterable[Property]):
        self._properties = properties

    @property
    def properties(self):
        return self._properties

    @abstractmethod
    def get(self, key: str, scope: Union[discord.Guild, 'discord.abc.MessageableChannel'], recursive: bool = True) -> Optional[Any]:
        raise NotImplementedError

    @abstractmethod
    def set(self, key: str, value: Any, scope: Union[discord.Guild, 'discord.abc.MessageableChannel']):
        raise NotImplementedError

    @abstractmethod
    def remove(self, key: str, scope: Union[discord.Guild, 'discord.abc.MessageableChannel']):
        raise NotImplementedError


class FirestorePropertyManager(ScopedPropertyManager):

    def __init__(self, properties: Iterable[Property]):
        super().__init__(properties)
        self._default_properties = {p.key: p.default for p in self.properties}
        self._firestore_client = firestore.Client()

        # Maintain a cache so that we don't need to make too many requests to Firestore.
        self._cache = {}

        # This dictionary keeps track of which scopes are dirty and need to be fetched from Firestore next time
        self._dirty = {}

    def get(self, key: str, scope: Union[discord.Guild, 'discord.abc.MessageableChannel'], recursive: bool = True) -> Optional[Any]:

        # Check the cache
        if scope in self._cache and not self._dirty[scope]:
            data = self._cache[scope]
        else:
            # The data was either not in the cache, or was in the cache but it's dirty so we need to fetch it again
            snapshot = self._get_snapshot(scope)
            data = snapshot.to_dict() if snapshot.exists else {}

            # Add data to cache
            self._cache[scope] = data
            self._dirty[scope] = False

        if key in data:
            return data[key]

        if recursive:
            if isinstance(scope, (discord.Guild, discord.DMChannel)):

                # The guild did not have the requested property, maybe the default properties has it
                if key in self._default_properties:
                    value = self._default_properties[key]
                    return value

            else:

                guild = None
                try:
                    guild = scope.guild
                except Exception:
                    logger.error(f'Scope does not have guild: {type(scope)} "{scope}"')

                if guild:
                    # The channel did not have the requested property, maybe the guild has it
                    return self.get(key, guild)

                raise TypeError(f'Unsupported scope: {type(scope)} "{scope}"')

        return None

    def get_property(self, key):
        for p in self.properties:
            if p.key == key:
                return p
        return None

    def set(self, key: str, value: Any, scope: Union[discord.Guild, 'discord.abc.MessageableChannel']):

        prop = self.get_property(key)
        if prop is None:
            raise InvalidKeyError(key)

        # Convert value to correct type
        if isinstance(value, str):
            value = prop.parse(value)

        # Make sure the key and value are valid
        if not prop.is_valid(value):
            raise InvalidValueError(key, value)

        self._get_snapshot(scope).reference.set({key: value}, merge=True)
        self._dirty[scope] = True

    def remove(self, key: str, scope: Union[discord.Guild, 'discord.abc.MessageableChannel']):

        # Make sure this is a valid property
        prop = self.get_property(key)
        if prop is None:
            raise InvalidKeyError(key)

        # Remove the key from the document
        snapshot = self._get_snapshot(scope)
        if snapshot.exists:
            snapshot.reference.update({
                key: firestore.DELETE_FIELD
            })
            self._dirty[scope] = True

    def _get_snapshot(self, scope: Union[discord.Guild, 'discord.abc.MessageableChannel']) -> firestore.DocumentSnapshot:
        if isinstance(scope, discord.Guild):
            guild_document = self._firestore_client.collection('guilds').document(str(scope.id))
            return guild_document.get()
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
            guild_id = None
            try:
                guild_id = scope.guild.id
            except Exception:
                logger.error(f'No guild ID for scope: {type(scope)} {scope}')

            if guild_id:
                guild_document = self._firestore_client.collection('guilds').document(str(guild_id))
                channel_document = guild_document.collection('channels').document(str(scope.id))
                channel_snapshot = channel_document.get()
                return channel_snapshot
        raise TypeError(f'Unknown scope: {type(scope)} "{scope}"')

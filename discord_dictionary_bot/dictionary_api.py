import asyncio
from abc import ABC, abstractmethod
import aiohttp
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional

from . import analytics

# Set up logging
logger = logging.getLogger(__name__)


class DictionaryAPI(ABC):

    @abstractmethod
    async def define(self, word: str) -> List[Dict[str, str]]:
        """
        Get the definitions for the specified word. The returned format should be as follows:
        [
        {word_type: 'str', definition: 'str'},
        ...
        ]
        :param word: The word to define.
        :return: A list of definitions for the specified word.
        """
        return []

    def __repr__(self):
        return f'[{type(self).__name__}]'

    @abstractmethod
    def id(self) -> str:
        raise NotImplementedError

    @property
    @abstractmethod
    def name(self) -> str:
        raise NotImplementedError


async def handle_default_status(api, word, response):
    if response.status == 401:
        logger.error(f'{api} Permission denied! You are probably using an invalid API key. {{Status code: {response.status}, Word: "{word}"}}')
        return False
    elif response.status == 404:
        logger.info(f'{api} Could not find a definition for "{word}"')
        return False

    if response.status != 200:
        logger.error(f'{api} Error getting definition! {{status_code: {response.status}, word: "{word}", content: "{await response.text()}"}}')
        return False

    return True


class RequestLimiter:

    def __init__(self, request_limit: int, request_period: timedelta):
        self._request_limit = request_limit
        self._request_period = request_period
        self._request_period_start = datetime.now()

        # Number of requests made in the current time period
        self._request_count = 0

    @property
    def request_limit(self):
        return self._request_limit

    @property
    def request_count(self):
        return self._request_count

    def can_request(self):
        return self._request_count < self._request_limit

    def request(self):
        # Reset request count
        if datetime.now() > self._request_period_start + self._request_period:
            self._request_count = 0
            self._request_period_start = datetime.now()
            logger.info(f'{self} Reset request count.')

        # Increment request count
        self._request_count += 1


class OwlBotDictionaryAPI(DictionaryAPI):

    def __init__(self, token: str):
        self._token = token
        self._aio_client_session = aiohttp.ClientSession()

    async def define(self, word: str) -> List[Dict[str, str]]:
        headers = {'Authorization': f'Token {self._token}'}
        async with self._aio_client_session.get('https://owlbot.info/api/v4/dictionary/' + word.replace(' ', '%20'), headers=headers) as response:

            if not await handle_default_status(self, word, response):
                return []

            logger.info(f'{self} {{status_code: {response.status}, word: "{word}"}}')

            response_json = await response.json()

            result = []
            for d in response_json['definitions']:
                result.append({
                    'word_type': d['type'],
                    'definition': d['definition']
                })

        return result

    def id(self) -> str:
        return 'owlbot'

    @property
    def name(self) -> str:
        return 'Owlbot'


class UnofficialGoogleAPI(DictionaryAPI):
    """
    https://github.com/meetDeveloper/freeDictionaryAPI
    """

    def __init__(self):
        self._aio_client_session = aiohttp.ClientSession()

    async def define(self, word: str) -> List[Dict[str, str]]:
        async with self._aio_client_session.get('https://api.dictionaryapi.dev/api/v2/entries/en/' + word.replace(' ', '%20') + '?format=json') as response:

            if not await handle_default_status(self, word, response):
                return []

            logger.info(f'{self} {{status_code: {response.status}, word: "{word}"}}')

            result = []

            response_json = await response.json()
            for d in response_json[0]['meanings']:
                definition = {
                    'word_type': d['partOfSpeech'],
                    'definition': d['definitions'][0]['definition']
                }
                result.append(definition)

        return result

    def id(self) -> str:
        return 'unofficial_google'

    @property
    def name(self) -> str:
        return 'Unofficial Google API'


class MerriamWebsterAPI(DictionaryAPI, ABC):

    def __init__(self, api_key):
        self._api_key = api_key
        self._aio_client_session = aiohttp.ClientSession()
        self._request_limiter = RequestLimiter(1000, timedelta(days=1))

    def _get_short_definitions(self, response_json) -> []:

        # Sometimes the response is an empty list
        if len(response_json) == 0:
            return []

        # The response returns a list for some reason, the first item is supposed
        # to have the definition.
        response_definition = response_json[0]

        # Sometimes it doesn't return the definition
        if isinstance(response_definition, str):
            logger.error(f'{self} Bad response format: {response_json}')
            return []

        results = []

        word_type = response_definition['fl']

        for definition in response_definition['shortdef']:
            results.append({
                'word_type': word_type,
                'definition': definition
            })

        return results


class MerriamWebsterCollegiateAPI(MerriamWebsterAPI):

    async def define(self, word: str) -> List[Dict[str, str]]:

        # Limit requests
        if self._request_limiter.can_request():
            self._request_limiter.request()
            logger.info(f'{self} Request {self._request_limiter.request_count} / {self._request_limiter.request_limit}')
        else:
            logger.critical(f'{self} Request limit reached!')
            return []

        word = word.lower()

        async with self._aio_client_session.get('https://dictionaryapi.com/api/v3/references/collegiate/json/' + word.replace(' ', '%20') + '?key=' + self._api_key) as response:

            if not await handle_default_status(self, word, response):
                return []

            result = self._get_short_definitions(await response.json())

        return result

    def id(self) -> str:
        return 'merriam_webster_collegiate'

    @property
    def name(self) -> str:
        return 'Merriam Webster Collegiate'


class MerriamWebsterMedicalAPI(MerriamWebsterAPI):

    async def define(self, word: str) -> List[Dict[str, str]]:

        # Limit requests
        if self._request_limiter.can_request():
            self._request_limiter.request()
            logger.info(f'{self} Request {self._request_limiter.request_count} / {self._request_limiter.request_limit}')
        else:
            logger.critical(f'{self} Request limit reached!')
            return []

        word = word.lower()

        async with self._aio_client_session.get('https://dictionaryapi.com/api/v3/references/medical/json/' + word.replace(' ', '%20') + '?key=' + self._api_key) as response:

            if not await handle_default_status(self, word, response):
                return []

            result = self._get_short_definitions(await response.json())

        return result

    def id(self) -> str:
        return 'merriam_webster_medical'

    @property
    def name(self) -> str:
        return 'Merriam Webster Medical'


class RapidWordsAPI(DictionaryAPI):

    def __init__(self, api_key):
        self._api_key = api_key
        self._aio_client_session = aiohttp.ClientSession()
        self._request_limiter = RequestLimiter(2000, timedelta(days=1))

    async def define(self, word: str) -> List[Dict[str, str]]:

        if self._request_limiter.can_request():
            self._request_limiter.request()
            logger.info(f'{self} Request {self._request_limiter.request_count} / {self._request_limiter.request_limit}')
        else:
            logger.critical(f'{self} Request limit reached!')
            return []

        headers = {
            'x-rapidapi-key': self._api_key,
            'x-rapidapi-host': 'wordsapiv1.p.rapidapi.com'
        }
        async with self._aio_client_session.get('https://wordsapiv1.p.rapidapi.com/words/' + word.replace(' ', '%20'), headers=headers) as response:

            if not await handle_default_status(self, word, response):
                return []

            logger.info(f'{self} {{status_code: {response.status}, word: "{word}"}}')

            results = []

            response_json = await response.json()

            if 'results' not in response_json:
                logger.warning(f'{self} No results for word: "{word}"')
                return []

            results_json = response_json['results']
            for definition_json in results_json:
                results.append({
                    'word_type': definition_json['partOfSpeech'],
                    'definition': definition_json['definition'] + '.'
                })

        return results

    def id(self) -> str:
        return 'rapid_words'

    @property
    def name(self) -> str:
        return 'Rapid Words'


class SequentialDictionaryAPI(DictionaryAPI):
    """
    This class is a wrapper for other 'DictionaryAPI's. The API's will be called sequentially until one succeeds.
    """

    def __init__(self, apis: List[DictionaryAPI], timeout: int = 2):
        """

        :param apis: A list of dictionary API's that will be called sequentially
        until one of them successfully returns.
        :param timeout: The maximum number of seconds to wait for a response
        from a DictionaryAPI. If a request times out, then the next available
        API will be called.
        """
        self._apis = apis
        self._timeout = timeout

    async def define(self, word: str) -> List[Dict[str, str]]:
        return (await self.define_with_source(word))[0]

    async def define_with_source(self, word: str) -> ([{str: str}], Optional[DictionaryAPI]):
        for api in self._apis:
            try:
                definitions = await asyncio.wait_for(api.define(word), self._timeout)
                if len(definitions) > 0:
                    analytics.log_dictionary_api_request(api.id(), True)
                    return definitions, api
                logger.warning(f'{api} did not return any definitions!')
            except aiohttp.ClientError as e:
                logger.warning(f'Client error for API "{api}"', exc_info=e)
            except asyncio.TimeoutError:
                logger.warning(f'{api} Took too long to respond!')
            analytics.log_dictionary_api_request(api.id(), False)
        return [], None

    def id(self) -> str:
        return 'sequential'

    @property
    def name(self) -> str:
        return 'Sequential'

import asyncio
from abc import ABC, abstractmethod
import aiohttp
import logging
import re
from datetime import datetime, timedelta
import time

# Set up logging
logger = logging.getLogger(__name__)


class DictionaryAPI(ABC):

    @abstractmethod
    async def define(self, word: str) -> {}:
        """
        Get the definitions for the specified word. The returned format should be as follows:
        [
        {word_type: 'str', definition: 'str'}
        ]
        :param word: The word to define.
        :return: A list of definitions for the specified word.
        """
        pass

    def __repr__(self):
        return f'[{type(self).__name__}]'


class OwlBotDictionaryAPI(DictionaryAPI):

    def __init__(self, token: str):
        self._token = token
        self._aio_client_session = aiohttp.ClientSession()

    async def define(self, word: str) -> []:
        headers = {'Authorization': f'Token {self._token}'}
        async with self._aio_client_session.get('https://owlbot.info/api/v4/dictionary/' + word.replace(' ', '%20'), headers=headers) as response:

            if response.status == 401:
                logger.error(f'{self} Permission denied! You are probably using an invalid API key. {{Status code: {response.status}, Word: "{word}"}}')
                return []

            if response.status != 200:
                logger.error(f'{self} Error getting definition! {{status_code: {response.status}, word: "{word}", content: "{response.content}"}}')
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


class UnofficialGoogleAPI(DictionaryAPI):

    def __init__(self):
        self._aio_client_session = aiohttp.ClientSession()

    async def define(self, word: str) -> {}:
        async with self._aio_client_session.get('https://api.dictionaryapi.dev/api/v2/entries/en/' + word.replace(' ', '%20') + '?format=json') as response:

            if response.status != 404:
                logger.info(f'{self} Could not find a definition for "{word}"')
                return []

            if response.status != 200:
                logger.error(f'{self} Error getting definition! {{status_code: {response.status}, word: "{word}", content: "{response.content}"}}')
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


class MerriamWebsterAPI(DictionaryAPI):

    def __init__(self, api_key):
        self._api_key = api_key
        self._aio_client_session = aiohttp.ClientSession()

    async def define(self, word: str) -> {}:
        word = word.lower()

        async with self._aio_client_session.get('https://dictionaryapi.com/api/v3/references/collegiate/json/' + word.replace(' ', '%20') + '?key=' + self._api_key) as response:

            if response.status != 200:
                logger.error(f'{self} Error getting definition! {{status_code: {response.status}, word: "{word}", content: "{response.content}"}}')
                return []

            logger.info(f'{self} {{status_code: {response.status}, word: "{word}"}}')

            # TODO: Improve response parsing, sometimes it crashes
            result = self._get_first_definition_of_each_entry(word, await response.json())

        return result

    def _get_short_definitions(self, response_json) -> []:
        results = []

        word_type = response_json['fl']

        for definition in response_json['shortdef']:
            results.append({
                'word_type': word_type,
                'definition': definition
            })

        return results

    def _get_first_definition_of_each_entry(self, word: str, response_json) -> []:
        results = []

        for entry_json in response_json:

            # Ignore words that don't exactly match the requested word
            entry_id = entry_json['meta']['id'].lower()
            if ':' in entry_id:
                if entry_id.split(':')[0] != word:
                    continue
            elif entry_id != word:
                continue

            # Get word type
            word_type = entry_json['fl']

            # Get first "sense"
            sense = self._find_first_sense(entry_json['def'][0]['sseq'][0])

            # Get definition text from sense
            definition_text = self._get_text_from_dt(sense['dt'])

            # Clean up definition text (https://dictionaryapi.com/products/json#sec-2.tokens)
            definition_text = definition_text.replace('{bc}', '')
            definition_text = definition_text.replace('{ldquo}', '"')
            definition_text = definition_text.replace('{rdquo}', '"')
            definition_text = definition_text.replace('{p_br}', '\n')

            def replace(text, token):
                return re.sub(r'{' + token + r'}(.*){\\/' + token + r'}', r'\1', text)

            for token in ('b', 'inf', 'it', 'sc', 'sup', 'gloss', 'parahw', 'phrase', 'qword', 'wi'):
                definition_text = replace(definition_text, token)

            definition_text = re.sub(r'{\w*_link\|(.*?)\|*}', r'\1', definition_text)
            definition_text = re.sub(r'{mat\|(.*?)\|*}', r'\1', definition_text)
            definition_text = re.sub(r'{sx\|(.*?)\|*}', r'\1', definition_text)
            definition_text = re.sub(r'{dxt\|(.*?)\|*}', r'\1', definition_text)

            results.append({
                'word_type': word_type,
                'definition': definition_text
            })

        return results

    def _find_first_sense(self, sense_sequence):
        if sense_sequence[0] == 'sense':
            return sense_sequence[1]

        for sense in sense_sequence:
            if isinstance(sense, list):
                r = self._find_first_sense(sense)
                if r is not None:
                    return r

        return None

    def _get_text_from_dt(self, dt):
        if dt[0] == 'text':
            return dt[1]

        for item in dt:
            if isinstance(item, list):
                r = self._get_text_from_dt(item)
                if r is not None:
                    return r

        return None


class RapidWordsAPI(DictionaryAPI):

    def __init__(self, api_key):
        self._api_key = api_key
        self._aio_client_session = aiohttp.ClientSession()

        # Maximum number of request we can make in a 24hr period. If we exceed this, all future definition requests will return an empty response until the next time period
        self._request_limit = 2000

        self._request_period_start = datetime.now()

        # Number of requests made in the current time period
        self._request_count = 0

    async def define(self, word: str) -> {}:

        # Reset request count
        if datetime.now() > self._request_period_start + timedelta(days=1):
            self._request_count = 0
            self._request_period_start = datetime.now()
            logger.info(f'{self} Reset request count.')

        # Increment request count
        self._request_count += 1
        if self._request_count > self._request_limit:
            logger.critical(f'{self} Request limit reached!')
            return []

        headers = {
            'x-rapidapi-key': self._api_key,
            'x-rapidapi-host': 'wordsapiv1.p.rapidapi.com'
        }
        async with self._aio_client_session.get('https://wordsapiv1.p.rapidapi.com/words/' + word.replace(' ', '%20'), headers=headers) as response:

            if response.status == 200:
                logger.info(f'{self} {{status_code: {response.status}, word: "{word}"}}')
            else:
                logger.error(f'{self} Error getting definition! {{status_code: {response.status}, word: "{word}", content: "{response.content}"}}')
                return []

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


class BackupDictionaryAPI(DictionaryAPI):
    """
    This class is a wrapper for other 'DictionaryAPI's. The API's will be called sequentially until one succeeds.
    """

    def __init__(self, apis: [DictionaryAPI]):
        self._apis = apis

    async def define(self, word: str) -> {}:
        for api in self._apis:
            try:
                definitions = await asyncio.wait_for(api.define(word), 2)
                if len(definitions) > 0:
                    return definitions
            except aiohttp.ClientError as e:
                logger.error(f'Client error for API "{api}"', exc_info=e)
            except asyncio.TimeoutError:
                logger.warning(f'{api} Took too long to respond!')
        return []

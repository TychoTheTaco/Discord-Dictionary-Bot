from abc import ABC, abstractmethod
import requests
import logging
import re
from datetime import datetime, timedelta

# Set up logging
logger = logging.getLogger(__name__)


class DictionaryAPI(ABC):

    @abstractmethod
    def define(self, word: str) -> {}:
        pass

    def __repr__(self):
        return f'[{type(self).__name__}]'


class OwlBotDictionaryAPI(DictionaryAPI):

    def __init__(self, token: str):
        super().__init__()
        self._token = token

    def define(self, word: str) -> []:
        """
        Get the definitions for the specified word. The format is:
        [
        {word_type: 'str', definition: 'str'}
        ]
        :param word: The word to define.
        :return:
        """
        headers = {'Authorization': f'Token {self._token}'}
        response = requests.get('https://owlbot.info/api/v2/dictionary/' + word.replace(' ', '%20') + '?format=json', headers=headers)

        if response.status_code == 401:
            logger.error(f'{self} Permission denied! You are probably using an invalid API key. {{Status code: {response.status_code}, Word: "{word}"}}')
            return []

        if response.status_code != 200:
            logger.error(f'{self} Error getting definition! {{status_code: {response.status_code}, word: "{word}", content: "{response.content}"}}')
            return []

        try:
            definitions = response.json()
        except ValueError:  # Catch a ValueError here because sometimes requests uses simplejson instead of json as a backend
            logger.error(f'{self} Failed to parse response: {response}')
            return []

        result = []
        for d in definitions:
            definition = {
                'word_type': d['type'],
                'definition': d['definition']
            }
            result.append(definition)

        return result


class UnofficialGoogleAPI(DictionaryAPI):

    def define(self, word: str) -> {}:
        response = requests.get('https://api.dictionaryapi.dev/api/v2/entries/en/' + word.replace(' ', '%20') + '?format=json')

        if response.status_code != 200:
            logger.error(f'{self} Error getting definition! {{status_code: {response.status_code}, word: "{word}", content: "{response.content}"}}')
            return []

        logger.info(f'{self} {{status_code: {response.status_code}, word: "{word}"}}')

        result = []
        try:
            response_json = response.json()
            for d in response_json[0]['meanings']:
                definition = {
                    'word_type': d['partOfSpeech'],
                    'definition': d['definitions'][0]['definition']
                }
                result.append(definition)
        except Exception as e:
            logger.error(f'{self} Failed to parse API response: {e}')

        return result


class MerriamWebsterAPI(DictionaryAPI):

    def __init__(self, api_key):
        self._api_key = api_key

    def define(self, word: str) -> {}:
        word = word.lower()
        response = requests.get('https://dictionaryapi.com/api/v3/references/collegiate/json/' + word.replace(' ', '%20') + '?key=' + self._api_key)

        if response.status_code != 200:
            logger.error(f'{self} Error getting definition! {{status_code: {response.status_code}, word: "{word}", content: "{response.content}"}}')
            return []

        logger.info(f'{self} {{status_code: {response.status_code}, word: "{word}"}}')

        result = []
        try:
            result = self._get_first_definition_of_each_entry(word, response.json())
        except Exception:
            logger.error(f'{self} Failed to parse API response!', exc_info=True)

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

        # Maximum number of request we can make in a 24hr period. If we exceed this, all future definition requests will return an empty response until the next time period
        self._request_limit = 2000

        self._request_period_start = datetime.now()

        # Number of requests made in the current time period
        self._request_count = 0

    def define(self, word: str) -> {}:

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
        response = requests.get('https://wordsapiv1.p.rapidapi.com/words/' + word.replace(' ', '%20'), headers=headers)

        if response.status_code != 200:
            logger.error(f'{self} Error getting definition! {{status_code: {response.status_code}, word: "{word}", content: "{response.content}"}}')
            return []

        logger.info(f'{self} {{status_code: {response.status_code}, word: "{word}"}}')

        results = []
        try:
            response_json = response.json()

            if 'results' not in response_json:
                logger.warning(f'{self} No results for word: "{word}"')
                return []

            results_json = response_json['results']
            for definition_json in results_json:
                results.append({
                    'word_type': definition_json['partOfSpeech'],
                    'definition': definition_json['definition'] + '.'
                })

        except ValueError:  # Catch a ValueError here because sometimes requests uses simplejson instead of json as a backend
            logger.error(f'{self} Failed to parse response: {response}')
            return []

        return results

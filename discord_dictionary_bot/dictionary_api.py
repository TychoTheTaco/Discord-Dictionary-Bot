from abc import ABC, abstractmethod
import requests
from google.cloud import logging as gcp_logging
import logging

# Set up logging
logger = logging.getLogger(__name__)


class DictionaryAPI(ABC):

    def __init__(self):
        # Create logging client
        gcp_logging_client = gcp_logging.Client()
        self.gcp_logger = gcp_logging_client.logger('dictionary-api-requests')

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
            logger.error(f'{self} Error getting definition! {{Status code: {response.status_code}, Word: "{word}"}}')
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

        self.gcp_logger.log_struct({'word': word, 'response': {'status_code': response.status_code}})

        if response.status_code != 200:
            logger.error(f'{self} Error getting definition! {{Status code: {response.status_code}, Word: "{word}"}}')
            return []

        logger.info(f'{self} word: "{word}", status_code: {response.status_code}')

        result = []
        try:
            json = response.json()
            for d in json[0]['meanings']:
                definition = {
                    'word_type': d['partOfSpeech'],
                    'definition': d['definitions'][0]['definition']
                }
                result.append(definition)
        except Exception as e:
            logger.error(f'{self} Failed to parse API response: {e}')

        return result

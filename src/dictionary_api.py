from abc import ABC, abstractmethod
from m_logging import log
import requests
from google.cloud import logging


class DictionaryAPI(ABC):

    def __init__(self):
        # Create logging client
        logging_client = logging.Client()
        self.logger = logging_client.logger('discord-dictionary-bot-log')

    @abstractmethod
    def define(self, word: str) -> {}:
        pass

    def __repr__(self):
        return f'[{type(self).__name__}]'


class OwlBotDictionaryAPI(DictionaryAPI):

    def __init__(self, token: str):
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
            log(f'{self} Permission denied! You are probably using an invalid API key. {{Status code: {response.status_code}, Word: "{word}"}}', 'error')
            return []

        if response.status_code != 200:
            log(f'{self} Error getting definition! {{Status code: {response.status_code}, Word: "{word}"}}', 'error')
            return []

        try:
            definitions = response.json()
        except ValueError:  # Catch a ValueError here because sometimes requests uses simplejson instead of json as a backend
            log(f'{self} Failed to parse response: {response}')
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

        self.logger.log_text(f'{self} API Response: {response.status_code}')

        if response.status_code != 200:
            log(f'{self} Error getting definition! {{Status code: {response.status_code}, Word: "{word}"}}', 'error')
            return []

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
            log(f'{self} Failed to parse API response: {e}', 'error')

        return result

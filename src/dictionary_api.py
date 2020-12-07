from abc import ABC, abstractmethod
from m_logging import log
import requests


class DictionaryAPI(ABC):

    @abstractmethod
    def define(self, word: str) -> {}:
        pass


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

        if response.status_code != 200:
            log(f'Error getting definition! Status code: {response.status_code}; Word: "{word}"', 'error')
            return []

        try:
            definitions = response.json()
        except ValueError:  # Catch a ValueError here because sometimes requests uses simplejson instead of json as a backend
            log(f'Failed to parse response: {response}')
            return []

        result = []
        for d in definitions:
            definition = {
                'word_type': d['type'],
                'definition': d['definition']
            }
            result.append(definition)

        return result
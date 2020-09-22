import requests
import json


if __name__ == '__main__':
    word = '.'

    response = requests.get('https://owlbot.info/api/v2/dictionary/' + word.replace(' ', '%20') + '?format=json')
    print('RESPONSE:', response, response.content)

    try:
        j = response.json()
        print('JSON:', j)
    except json.JSONDecodeError:
        print('ERROR')

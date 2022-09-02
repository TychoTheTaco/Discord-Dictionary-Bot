import argparse
import os
import logging.config

from .discord_bot_client import DiscordBotClient
from .dictionary_api import OwlBotDictionaryAPI, UnofficialGoogleAPI, MerriamWebsterCollegiateAPI, RapidWordsAPI, MerriamWebsterMedicalAPI


def logging_filter(record):
    """
    Filter logs so that only records from this module are shown.
    :param record:
    :return:
    """
    return 'discord_dictionary_bot' in record.name or 'discord_dictionary_bot' in record.pathname or record.levelno >= logging.WARNING


# Set up logging
logging.basicConfig(format='%(asctime)s [%(name)s] [%(levelname)s] %(message)s', level=logging.DEBUG, datefmt='%m/%d/%Y %H:%M:%S')
logging.getLogger().handlers[0].addFilter(logging_filter)


def try_read_token(token_or_path: str) -> str:
    """
    Try to read from the given file. If the file can be read, return the file contents. Otherwise, return the argument.
    :param token_or_path:
    :return:
    """
    try:
        with open(token_or_path) as file:
            return file.read()
    except IOError:
        pass  # Ignore and assume the argument is a token string not a file path
    return token_or_path


def main():

    dictionary_api_options = {
        'google': {
            'class': UnofficialGoogleAPI
        },
        'owlbot': {
            'class': OwlBotDictionaryAPI,
            'key_arg_dest': 'owlbot_api_token',
            'key_arg_name': '--owlbot-api-token',
            'name': 'Owlbot'
        },
        'webster-collegiate': {
            'class': MerriamWebsterCollegiateAPI,
            'key_arg_dest': 'webster_collegiate_api_token',
            'key_arg_name': '--webster-collegiate-api-token',
            'name': 'Merriam Webster Collegiate'
        },
        'webster-medical': {
            'class': MerriamWebsterMedicalAPI,
            'key_arg_dest': 'webster_medical_api_token',
            'key_arg_name': '--webster-medical-api-token',
            'name': 'Merriam Webster Medical'
        },
        'rapid-words': {
            'class': RapidWordsAPI,
            'key_arg_dest': 'rapid_words_api_token',
            'key_arg_name': '--rapid-words-api-token',
            'name': 'RapidWords'
        },
    }

    # Parse arguments
    parser = argparse.ArgumentParser()
    parser.add_argument('--discord-token',
                        help='Token to use when running the bot. You can either use the raw token string or a path to a text file containing the token.',
                        dest='discord_bot_token',
                        default='discord_token.txt')
    parser.add_argument('--ffmpeg-path',
                        help='Path to ffmpeg executable.',
                        dest='ffmpeg_path',
                        default='ffmpeg')
    parser.add_argument('--google-credentials-path',
                        help='Path to Google application credentials JSON file.',
                        dest='google_credentials_path',
                        default='google_credentials.json')
    parser.add_argument('--dictionary-api',
                        help='A list of dictionary API\'s to use for fetching definitions. These should be in order of priority and separated by comma\'s. Available API\'s are '
                             + ', '.join(['\'' + x + '\'' for x in dictionary_api_options])
                             + '. Some API\'s require tokens that must be provided with the appropriate arguments.',
                        dest='dictionary_api',
                        default=next(iter(dictionary_api_options)))

    # Add API key arguments for dictionary API's
    for k, v in dictionary_api_options.items():
        if 'key_arg_dest' not in v or 'key_arg_name' not in v:
            continue

        parser.add_argument(v['key_arg_name'],
                            help=f'The token to use for the {v["name"]} dictionary API. You can use either the raw token string or a path to a text file containing the token.',
                            dest=v['key_arg_dest'],
                            default=f'{v["key_arg_dest"]}.txt')
    args = parser.parse_args()

    # Set Google API credentials
    os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = args.google_credentials_path

    # Check which dictionary API we should use
    dictionary_apis = []
    for name in args.dictionary_api.split(','):

        if name not in dictionary_api_options:
            print(f'Invalid dictionary API: "{name}"')
            return

        api_info = dictionary_api_options[name]

        # If this API requires a key, try to load it now
        if 'key_arg_dest' in api_info:
            if api_info['key_arg_dest'] not in args:
                print(f'You must specify an API token with {api_info["key_arg_name"]} to use the {api_info["name"]} dictionary API!')
                return

            api_token = try_read_token(vars(args)[api_info["key_arg_dest"]])
            dictionary_apis.append(api_info["class"](api_token))
        else:
            dictionary_apis.append(api_info["class"]())

    # Start client
    bot = DiscordBotClient(dictionary_apis, args.ffmpeg_path)
    bot.run(try_read_token(args.discord_bot_token))


if __name__ == '__main__':
    main()

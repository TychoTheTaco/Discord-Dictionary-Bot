import argparse
import os
import logging.config
import google.cloud.logging
from google.cloud.logging.handlers import CloudLoggingHandler
from .discord_bot_client import DiscordBotClient
from .dictionary_api import OwlBotDictionaryAPI, UnofficialGoogleAPI, MerriamWebsterAPI, RapidWordsAPI, BackupDictionaryAPI


def logging_filter(record):
    """
    Filter logs so that only records from this module are shown.
    :param record:
    :return:
    """
    return 'discord_dictionary_bot' in record.name or 'discord_dictionary_bot' in record.pathname


def gcp_logging_filter(record):
    return 'google.cloud.logging_v2.handlers.transports.background_thread' not in record.name


# Set up logging
logging.basicConfig(format='%(asctime)s [%(name)s] [%(levelname)s] %(message)s', level=logging.DEBUG, datefmt='%m/%d/%Y %H:%M:%S')
logging.getLogger().handlers[0].addFilter(gcp_logging_filter)


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
    dictionary_api_options = ('google', 'owlbot', 'webster', 'rapid-words')
    parser.add_argument('--dictionary-api',
                        help='A list of dictionary API\'s to use for fetching definitions. These should be in order of priority and separated by comma\'s. Available API\'s are '
                             + ', '.join(['\'' + x + '\'' for x in dictionary_api_options])
                             + '. Some API\'s require tokens that must be provided with the appropriate arguments.',
                        dest='dictionary_api',
                        default=dictionary_api_options[0])
    parser.add_argument('--owlbot-api-token',
                        help='The token to use for the Owlbot dictionary API. You can use either the raw token string or a path to a text file containing the token.',
                        dest='owlbot_api_token',
                        default='owlbot_api_token.txt')
    parser.add_argument('--webster-api-token',
                        help='The token to use for the Merriam Webster dictionary API. You can use either the raw token string or a path to a text file containing the token.',
                        dest='webster_api_token',
                        default='webster_api_token.txt')
    parser.add_argument('--rapid-words-api-token',
                        help='The token to use for the RapidAPI WordsAPI dictionary API. You can use either the raw token string or a path to a text file containing the token.',
                        dest='rapid_words_api_token',
                        default='rapid_words_api_token.txt')
    args = parser.parse_args()

    # Set Google API credentials
    os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = args.google_credentials_path

    # Set up GCP logging
    gcp_logging_client = google.cloud.logging.Client()
    gcp_logging_handler = CloudLoggingHandler(gcp_logging_client, name='discord-dictionary-bot')
    gcp_logging_handler.addFilter(gcp_logging_filter)
    logging.getLogger().addHandler(gcp_logging_handler)

    # Check which dictionary API we should use
    dictionary_apis = []
    for name in args.dictionary_api.split(','):

        if name == 'google':
            dictionary_apis.append(UnofficialGoogleAPI())
        elif name == 'owlbot':

            if 'owlbot_api_token' not in args:
                print(f'You must specify an API token with --owlbot-api-token to use the owlbot dictionary API!')
                return

            # Read owlbot API token from file
            owlbot_api_token = try_read_token(args.owlbot_api_token)

            dictionary_apis.append(OwlBotDictionaryAPI(owlbot_api_token))

        elif name == 'webster':

            if 'webster_api_token' not in args:
                print(f'You must specify an API token with --webster-api-token to use the Merriam Webster dictionary API!')
                return

            # Read API token from file
            webster_api_token = try_read_token(args.webster_api_token)

            dictionary_apis.append(MerriamWebsterAPI(webster_api_token))

        elif name == 'rapid-words':

            if 'rapid_words_api_token' not in args:
                print(f'You must specify an API token with --rapid-words-api-token to use the Rapid API WordsAPI dictionary API!')
                return

            # Read API token from file
            rapid_words_api_token = try_read_token(args.rapid_words_api_token)

            dictionary_apis.append(RapidWordsAPI(rapid_words_api_token))

        else:
            print(f'Invalid dictionary API: {args.dictionary_api}')
            return

    # Start client
    bot = DiscordBotClient(BackupDictionaryAPI(dictionary_apis), args.ffmpeg_path)
    bot.run(try_read_token(args.discord_bot_token))


if __name__ == '__main__':
    main()

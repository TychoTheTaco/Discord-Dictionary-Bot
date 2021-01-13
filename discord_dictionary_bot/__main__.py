import argparse
import os
import logging.config

import discord
import google.cloud.logging
from google.cloud.logging.handlers import CloudLoggingHandler

from discord_dictionary_bot.dictionary_api import OwlBotDictionaryAPI, UnofficialGoogleAPI
from discord_dictionary_bot.dictionary_bot_client import DictionaryBotClient


def logging_filter_bot_only(record):
    return record.name.startswith('discord_dictionary_bot')


# Set up logging
logging.basicConfig(format='%(asctime)s [%(name)s] [%(levelname)s] %(message)s', level=logging.DEBUG, datefmt='%m/%d/%Y %I:%M:%S %p')
logging.getLogger().handlers[0].addFilter(logging_filter_bot_only)


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
    parser.add_argument('--dictionary-api',
                        help='The dictionary API to use for fetching definitions.',
                        dest='dictionary_api',
                        default='google',
                        choices=['google', 'owlbot'])
    parser.add_argument('--owlbot-api-token',
                        help='The token to use for the Owlbot dictionary API. You can use either the raw token string or a path to a text file containing the token.',
                        dest='owlbot_api_token',
                        default='owlbot_api_token.txt')
    args = parser.parse_args()

    # Set Google API credentials
    os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = args.google_credentials_path

    # Set up GCP logging
    gcp_logging_client = google.cloud.logging.Client()
    gcp_logging_handler = CloudLoggingHandler(gcp_logging_client, name='discord-dictionary-bot')
    gcp_logging_handler.addFilter(logging_filter_bot_only)
    logging.getLogger().addHandler(gcp_logging_handler)

    # Read discord bot token from file
    try:
        with open(args.discord_bot_token) as file:
            args.discord_bot_token = file.read()
    except IOError:
        pass  # Ignore and assume the argument is a token string not a file path

    # Check which dictionary API we should use
    if args.dictionary_api == 'google':
        dictionary_api = UnofficialGoogleAPI()
    elif args.dictionary_api == 'owlbot':

        if 'owlbot_api_token' not in args:
            print(f'You must specify an API token with --owlbot-api-token to use the owlbot dictionary API!')
            return

        # Read owlbot API token from file
        try:
            with open(args.owlbot_api_token) as file:
                args.owlbot_api_token = file.read()
        except IOError:
            pass  # Ignore and assume the argument is a token string not a file path

        dictionary_api = OwlBotDictionaryAPI(args.owlbot_api_token)

    else:
        print(f'Invalid dictionary API: {args.dictionary_api}')
        return

    # Start client
    intents = discord.Intents.default()
    intents.members = True  # The members intent is required for slash commands to work correctly. It is used to lookup a 'discord.Member' based on their user ID.
    client = DictionaryBotClient(args.ffmpeg_path, dictionary_api, intents=intents)
    client.run(args.discord_bot_token)


if __name__ == '__main__':
    main()

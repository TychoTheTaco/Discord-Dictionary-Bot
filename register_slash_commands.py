import requests
import argparse

HEADERS = None
DISCORD_APP_ID = None


def register(json, guild_id):
    if guild_id is None:
        result = requests.post(f'https://discord.com/api/v8/applications/{DISCORD_APP_ID}/commands', json=json, headers=HEADERS)
        print(result)
    else:
        result = requests.post(f'https://discord.com/api/v8/applications/{DISCORD_APP_ID}/guilds/{guild_id}/commands', json=json, headers=HEADERS)
        print(result)


if __name__ == '__main__':

    # Parse arguments
    parser = argparse.ArgumentParser()
    parser.add_argument('--discord-token',
                        help='You can either use the raw token string or a path to a text file containing the token.',
                        dest='discord_bot_token',
                        default='discord_token.txt')
    parser.add_argument('--discord-app-id',
                        help='You can either use the raw id string or a path to a text file containing the id.',
                        dest='discord_app_id',
                        default='discord_app_id.txt')
    args = parser.parse_args()

    # Read discord bot token from file
    try:
        with open(args.discord_bot_token) as file:
            args.discord_bot_token = file.read()
    except IOError:
        pass  # Ignore and assume the argument is a token string not a file path

    # Read discord app id from file
    try:
        with open(args.discord_app_id) as file:
            args.discord_app_id = file.read()
    except IOError:
        pass  # Ignore and assume the argument is an id string not a file path

    headers = {
        'Authorization': f'Bot {args.discord_bot_token}'
    }
    print(headers)

    HEADERS = headers
    MY_GUILD_ID = None  # Use None for global commands
    DISCORD_APP_ID = args.discord_app_id

    # Help command
    register({
        'name': 'help',
        'description': 'Shows you a helpful message.'
    }, MY_GUILD_ID)

    # Define command
    register({
        'name': 'define',
        'description': 'Gets the definition of a word.',
        'options': [
            {
                'name': 'word',
                'description': 'The word to define.',
                'type': 3,
                'required': True
            },
            {
                'name': 'text_to_speech',
                'description': 'Reads the definition to you.',
                'type': 5
            },
            {
                'name': 'language',
                'description': 'The language to use when reading the definition.',
                'type': 3,
            }
        ]
    }, MY_GUILD_ID)

    # Next command
    register({
        'name': 'next',
        'description': 'If the bot is currently reading out a definition, this will make it skip to the next one.'
    }, MY_GUILD_ID)

    # Property command
    register({
        'name': 'property',
        'description': 'Change the bot\'s properties for a channel or server.',
        'options': [
            {
                'name': 'guild',
                'description': 'Modify guild properties.',
                'type': 2,
                'options': [
                    {
                        'name': 'list',
                        'description': 'List guild properties.',
                        'type': 1
                    },
                    {
                        'name': 'set',
                        'description': 'Set guild properties.',
                        'type': 1,
                        'options': [
                            {
                                'name': 'name',
                                'description': 'Property name.',
                                'type': 3,
                                'required': True
                            },
                            {
                                'name': 'value',
                                'description': 'Property value.',
                                'type': 3,
                                'required': True
                            }
                        ]
                    }
                ]
            },
            {
                'name': 'channel',
                'description': 'Modify channel properties.',
                'type': 2,
                'options': [
                    {
                        'name': 'list',
                        'description': 'List channel properties.',
                        'type': 1
                    },
                    {
                        'name': 'set',
                        'description': 'Set channel properties.',
                        'type': 1,
                        'options': [
                            {
                                'name': 'name',
                                'description': 'Property name.',
                                'type': 3,
                                'required': True
                            },
                            {
                                'name': 'value',
                                'description': 'Property value.',
                                'type': 3,
                                'required': True
                            }
                        ]
                    },
                    {
                        'name': 'delete',
                        'description': 'Delete channel properties.',
                        'type': 1,
                        'options': [
                            {
                                'name': 'name',
                                'description': 'The name of the property to delete.',
                                'type': 3,
                                'required': True
                            }
                        ]
                    }
                ]
            }
        ]
    }, MY_GUILD_ID)

    # Stop command
    register({
        'name': 'stop',
        'description': 'Makes this bot stop talking and removes all definition requests.'
    }, MY_GUILD_ID)

    # Lang command
    register({
        'name': 'languages',
        'description': 'Shows the list of supported languages for text to speech.',
        'options': [
            {
                'name': 'verbose',
                'description': 'Prints all supported languages (This will spam the chat).',
                'type': 5
            }
        ]
    }, MY_GUILD_ID)

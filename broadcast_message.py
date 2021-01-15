import argparse
import asyncio

import discord


def main():
    # Parse arguments
    parser = argparse.ArgumentParser()
    parser.add_argument('--discord-token',
                        help='Token to use when running the bot. You can either use the raw token string or a path to a text file containing the token.',
                        dest='discord_bot_token',
                        default='discord_token.txt')
    args = parser.parse_args()

    # Read discord bot token from file
    try:
        with open(args.discord_bot_token) as file:
            args.discord_bot_token = file.read()
    except IOError:
        pass  # Ignore and assume the argument is a token string not a file path

    # Create client
    client = discord.Client()

    @client.event
    async def on_ready():
        message = 'Hello everyone, Dictionary Bot now supports using [Slash Commands](https://discord.com/developers/docs/interactions/slash-commands)! To use them, you just need to grant the bot an ' \
                  '[additional permission](https://discord.com/oauth2/authorize?client_id=755688136851324930&permissions=3165184&scope=bot%20applications.commands). ' \
                  'You can still use the bot in the same way as before if you don\'t want to use the new Slash Commands. Note that you may have to restart Discord to see the new Slash Commands.'
        channel_ids = [
            799455809808891986
        ]

        CONFIRM_MESSAGE = 'Yes, I\'m sure'
        user_input = input(f'You are about to broadcast a message to {len(channel_ids)} channels! If you are absolutely sure you want to do this, type "{CONFIRM_MESSAGE}" (without quotes):\n')
        if user_input != CONFIRM_MESSAGE:
            print('Aborting broadcast')
            return

        print(f'Broadcasting message to {len(channel_ids)} channels!')
        for channel_id in channel_ids:
            channel: discord.TextChannel = client.get_channel(channel_id)
            print(f'Sending message to "{channel}"')

            e = discord.Embed()
            e.title = 'Slash Commands Support'
            e.description = message
            asyncio.run_coroutine_threadsafe(channel.send(embed=e), client.loop)
        print('Broadcast complete')

    # Start client
    client.run(args.discord_bot_token)


if __name__ == '__main__':
    main()

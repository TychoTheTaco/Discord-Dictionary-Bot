import pathlib
import argparse
import utils
from bot import DictionaryBotClient
import os

TOKEN_FILE_PATH = pathlib.Path('../token.txt')

# Set environment variables
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = '../credentials.json'

if __name__ == '__main__':

    # Parse arguments
    parser = argparse.ArgumentParser()
    parser.add_argument('-t', help='Token to use when running the bot.', dest='token', default=None)
    parser.add_argument('-f', help='Path to ffmpeg executable', dest='ffmpeg_path', default='ffmpeg')
    args = parser.parse_args()

    ffmpeg_path = args.ffmpeg_path
    token = args.token if args.token is not None else utils.get_token(path='../token.txt')

    # Start client
    client = DictionaryBotClient(ffmpeg_path)
    client.run(token)

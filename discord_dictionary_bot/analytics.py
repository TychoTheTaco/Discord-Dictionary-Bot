import logging
import io
import json
import datetime
import threading
from typing import Union

from google.cloud import bigquery
import discord
from discord.ext import commands
from discord_slash import SlashContext

# Set up logging
logger = logging.getLogger(__name__)


def run_on_another_thread(function):
    """
    This decorator will run the decorated function in another thread, starting it immediately.
    :param function:
    :return:
    """

    def f(*args, **kargs):
        threading.Thread(target=function, args=[*args, *kargs]).start()

    return f


def _is_blacklisted(context: commands.Context):
    # Ignore dev server
    if isinstance(context.channel, discord.TextChannel) and context.channel.guild.id in [454852632528420876, 799455809297842177]:
        logger.info(f'Ignoring analytics submission for development server.')
        return True
    return False


def get_guild_and_channel_id(context: commands.Context):
    if isinstance(context.channel, discord.TextChannel):
        return context.channel.guild.id, context.channel.id
    elif isinstance(context.channel, discord.DMChannel):
        return None, context.channel.id


@run_on_another_thread
def log_command(command_name: str, is_slash: bool, context: Union[commands.Context, SlashContext]):

    if _is_blacklisted(context):
        return

    client = bigquery.Client()
    job_config = bigquery.LoadJobConfig(
        schema=[
            bigquery.SchemaField("command_name", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("is_slash", "BOOLEAN", mode="REQUIRED"),
            bigquery.SchemaField("guild_id", "INTEGER"),
            bigquery.SchemaField("channel_id", "INTEGER"),
            bigquery.SchemaField("time", "TIMESTAMP"),
        ],
        source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON,
        autodetect=True
    )

    guild_id, channel_id = get_guild_and_channel_id(context)
    data = {
        'command_name': command_name,
        'is_slash': is_slash,
        'guild_id': guild_id,
        'channel_id': channel_id,
        'time': datetime.datetime.now().isoformat()
    }

    data_as_file = io.StringIO(json.dumps(data))
    job = client.load_table_from_file(data_as_file, 'formal-scout-290305.analytics.commands', job_config=job_config)

    try:
        job.result()  # Waits for the job to complete.
    except Exception as e:
        raise Exception(f'Failed BigQuery upload job. Exception: {e} Errors: {job.errors}')


@run_on_another_thread
def log_definition_request(word: str, reverse: bool, text_to_speech: bool, language: str, context: commands.Context):

    if _is_blacklisted(context):
        return

    client = bigquery.Client()
    job_config = bigquery.LoadJobConfig(
        schema=[
            bigquery.SchemaField("word", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("reverse", "BOOLEAN", mode="REQUIRED"),
            bigquery.SchemaField("text_to_speech", "BOOLEAN", mode="REQUIRED"),
            bigquery.SchemaField("language", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("guild_id", "INTEGER"),
            bigquery.SchemaField("channel_id", "INTEGER"),
            bigquery.SchemaField("time", "TIMESTAMP"),
        ],
        source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON,
        autodetect=True
    )

    guild_id, channel_id = get_guild_and_channel_id(context)
    data = {
        'word': word,
        'reverse': reverse,
        'text_to_speech': text_to_speech,
        'language': language,
        'guild_id': guild_id,
        'channel_id': channel_id,
        'time': datetime.datetime.now().isoformat()
    }

    data_as_file = io.StringIO(json.dumps(data))
    job = client.load_table_from_file(data_as_file, 'formal-scout-290305.analytics.definition_requests', job_config=job_config)

    try:
        job.result()  # Waits for the job to complete.
    except Exception as e:
        raise Exception(f'Failed BigQuery upload job. Exception: {e} Errors: {job.errors}')

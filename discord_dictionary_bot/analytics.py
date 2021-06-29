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


def to_bq_file(items):
    return io.StringIO('\n'.join([json.dumps(x) for x in items]))


log_command_queue = []
log_command_lock = threading.Lock()


@run_on_another_thread
def log_command(command_name: str, is_slash: bool, context: Union[commands.Context, SlashContext]):
    with log_command_lock:

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

        log_command_queue.append(data)
        logger.debug(f'log_command_buffer: {len(log_command_queue)}')

        if len(log_command_queue) >= 10:
            logger.info('Uploading analytics!')
            data_as_file = to_bq_file(log_command_queue)

            job = client.load_table_from_file(data_as_file, 'formal-scout-290305.analytics.commands', job_config=job_config)

            try:
                job.result()  # Waits for the job to complete.
                log_command_queue.clear()
            except Exception as e:
                raise Exception(f'Failed BigQuery upload job. Exception: {e} Errors: {job.errors}')


log_definition_request_buffer = []
log_definition_request_lock = threading.Lock()


@run_on_another_thread
def log_definition_request(word: str, reverse: bool, text_to_speech: bool, language: str, context: commands.Context):
    with log_definition_request_lock:
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

        log_definition_request_buffer.append(data)
        logger.debug(f'log_definition_request_buffer: {len(log_definition_request_buffer)}')

        if len(log_definition_request_buffer) >= 10:
            logger.info('Uploading analytics!')
            data_as_file = to_bq_file(log_definition_request_buffer)

            job = client.load_table_from_file(data_as_file, 'formal-scout-290305.analytics.definition_requests', job_config=job_config)

            try:
                job.result()  # Waits for the job to complete.
                log_definition_request_buffer.clear()
            except Exception as e:
                raise Exception(f'Failed BigQuery upload job. Exception: {e} Errors: {job.errors}')


log_dictionary_api_request_buffer = []
log_dictionary_api_request_lock = threading.Lock()


@run_on_another_thread
def log_dictionary_api_request(dictionary_api_name: str, success: bool):
    with log_dictionary_api_request_lock:

        client = bigquery.Client()
        job_config = bigquery.LoadJobConfig(
            schema=[
                bigquery.SchemaField("api_name", "STRING", mode="REQUIRED"),
                bigquery.SchemaField("success", "BOOLEAN", mode="REQUIRED"),
                bigquery.SchemaField("time", "TIMESTAMP", mode="REQUIRED")
            ],
            source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON,
            autodetect=True
        )

        data = {
            'api_name': dictionary_api_name,
            'success': success,
            'time': datetime.datetime.now().isoformat()
        }

        log_dictionary_api_request_buffer.append(data)
        logger.debug(f'log_definition_request_buffer: {len(log_dictionary_api_request_buffer)}')

        if len(log_dictionary_api_request_buffer) >= 10:
            logger.info('Uploading analytics!')
            data_as_file = to_bq_file(log_dictionary_api_request_buffer)

            job = client.load_table_from_file(data_as_file, 'formal-scout-290305.analytics.dictionary_api_requests', job_config=job_config)

            try:
                job.result()  # Waits for the job to complete.
                log_dictionary_api_request_buffer.clear()
            except Exception as e:
                raise Exception(f'Failed BigQuery upload job. Exception: {e} Errors: {job.errors}')

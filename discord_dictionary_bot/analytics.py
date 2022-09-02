import datetime
import io
import json
import logging
import threading
import time

import discord
from google.cloud import bigquery

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


def _is_blacklisted(channel: discord.TextChannel):
    # Ignore dev server
    if channel.guild.id in [454852632528420876, 799455809297842177]:
        logger.info(f'Ignoring analytics submission for development server.')
        return True
    return False


def to_bq_file(items):
    return io.StringIO('\n'.join([json.dumps(x) for x in items]))


def upload(config):
    client = bigquery.Client()
    logger.info(f'Uploading {len(config["queue"])} items to {config["table"]}')
    data_as_file = to_bq_file(config['queue'])

    job = client.load_table_from_file(data_as_file, config['table'], job_config=config['job_config'])

    try:
        job.result()  # Waits for the job to complete.
        config['queue'].clear()
    except Exception as e:
        logger.exception(f'Failed BigQuery upload job! Errors: {job.errors}', exc_info=e)


def create_qal_item(table, job_config):
    return {
        'queue': [],
        'lock': threading.Lock(),
        'table': table,
        'job_config': job_config
    }


# Queues and locks
qal = {
    'log_command': create_qal_item(
        'formal-scout-290305.analytics.commands',
        bigquery.LoadJobConfig(
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
    ),
    'log_definition_request': create_qal_item(
        'formal-scout-290305.analytics.definition_requests',
        bigquery.LoadJobConfig(
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
    ),
    'log_dictionary_api_request': create_qal_item(
        'formal-scout-290305.analytics.dictionary_api_requests',
        bigquery.LoadJobConfig(
            schema=[
                bigquery.SchemaField("api_name", "STRING", mode="REQUIRED"),
                bigquery.SchemaField("success", "BOOLEAN", mode="REQUIRED"),
                bigquery.SchemaField("time", "TIMESTAMP", mode="REQUIRED")
            ],
            source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON,
            autodetect=True
        )
    )
}


def analytics_uploader_thread():
    while True:

        time.sleep(60 * 5)

        for key, value in qal.items():
            try:
                queue = value['queue']
                lock = value['lock']
                with lock:
                    if len(queue) > 0:
                        upload(value)
            except Exception as e:
                logger.exception('Error uploading analytics!', exc_info=e)


threading.Thread(target=analytics_uploader_thread).start()


# @run_on_another_thread
# def log_command(command_name: str, is_slash: bool, context: Union[commands.Context, SlashContext]):
#     queue = qal['log_command']['queue']
#     with qal['log_command']['lock']:
#
#         if _is_blacklisted(context):
#             return
#
#         guild_id, channel_id = get_guild_and_channel_id(context)
#         data = {
#             'command_name': command_name,
#             'is_slash': is_slash,
#             'guild_id': guild_id,
#             'channel_id': channel_id,
#             'time': datetime.datetime.now().isoformat()
#         }
#
#         queue.append(data)


@run_on_another_thread
def log_definition_request(word: str, text_to_speech: bool, language: str, channel: discord.TextChannel):
    queue = qal['log_definition_request']['queue']
    with qal['log_definition_request']['lock']:
        if _is_blacklisted(channel):
            return

        data = {
            'word': word,
            'reverse': False,
            'text_to_speech': text_to_speech,
            'language': language,
            'guild_id': channel.guild.id,
            'channel_id': channel.id,
            'time': datetime.datetime.now().isoformat()
        }

        queue.append(data)


@run_on_another_thread
def log_dictionary_api_request(dictionary_api_name: str, success: bool):
    queue = qal['log_dictionary_api_request']['queue']
    with qal['log_dictionary_api_request']['lock']:
        data = {
            'api_name': dictionary_api_name,
            'success': success,
            'time': datetime.datetime.now().isoformat()
        }

        queue.append(data)

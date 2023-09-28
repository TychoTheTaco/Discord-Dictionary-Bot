import datetime
import io
import json
import logging
import threading

import discord
from discord import Interaction
from google.cloud import bigquery

# Set up logging
logger = logging.getLogger(__name__)


def _is_blacklisted(channel):
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
    'log_context_menu': create_qal_item(
        'formal-scout-290305.analytics.context_menu_usage',
        bigquery.LoadJobConfig(
            schema=[
                bigquery.SchemaField("name", "STRING", mode="REQUIRED"),
                bigquery.SchemaField("guild_id", "INTEGER"),
                bigquery.SchemaField("channel_id", "INTEGER"),
                bigquery.SchemaField("time", "TIMESTAMP", mode="REQUIRED"),
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


def upload_pending_analytics():
    for key, value in qal.items():
        try:
            queue = value['queue']
            lock = value['lock']
            with lock:
                if len(queue) > 0:
                    upload(value)
        except Exception as e:
            logger.exception('Error uploading analytics!', exc_info=e)


class AnalyticsUploader:

    def __init__(self):
        self._is_running = False
        self._stop_event = threading.Event()
        self._thread = threading.Thread(target=self._run)

    def start(self):
        if self._is_running:
            return
        self._is_running = True
        self._thread.start()

    def stop(self):
        if not self._is_running:
            return
        self._is_running = False
        self._stop_event.set()
        self._thread.join()

    def _run(self):
        logger.info('Started analytics uploader')
        while self._is_running:
            self._stop_event.wait(60 * 5)
            upload_pending_analytics()
        logger.info('Stopped analytics uploader')


def log_command(command_name: str, interaction: Interaction):
    queue = qal['log_command']['queue']
    with qal['log_command']['lock']:
        if _is_blacklisted(interaction.channel):
            return

        data = {
            'command_name': command_name,
            'is_slash': True,
            'guild_id': interaction.guild_id,
            'channel_id': interaction.channel_id,
            'time': datetime.datetime.now().isoformat()
        }

        queue.append(data)


def log_context_menu_usage(name: str, interaction: Interaction):
    queue = qal['log_context_menu']['queue']
    with qal['log_context_menu']['lock']:
        if _is_blacklisted(interaction.channel):
            return

        data = {
            'name': name,
            'guild_id': interaction.guild_id,
            'channel_id': interaction.channel_id,
            'time': datetime.datetime.now().isoformat()
        }

        queue.append(data)


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


def log_dictionary_api_request(dictionary_api_name: str, success: bool):
    queue = qal['log_dictionary_api_request']['queue']
    with qal['log_dictionary_api_request']['lock']:
        data = {
            'api_name': dictionary_api_name,
            'success': success,
            'time': datetime.datetime.now().isoformat()
        }

        queue.append(data)

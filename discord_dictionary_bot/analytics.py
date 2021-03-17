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


def _is_blacklisted(context):
    # Ignore dev server
    if isinstance(context.channel, discord.TextChannel) and context.channel.guild.id in [454852632528420876, 799455809297842177]:
        logger.info(f'Ignoring analytics submission for development server.')
        return True
    return False


def _log_command(command_name: str, is_slash: bool, context: Union[commands.Context, SlashContext]):

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

    data = {
        'command_name': command_name,
        'is_slash': is_slash,
        'guild_id': None,
        'channel_id': None,
        'time': datetime.datetime.now().isoformat()
    }

    if isinstance(context.channel, discord.TextChannel):
        data['guild_id'] = context.channel.guild.id
        data['channel_id'] = context.channel.id
    elif isinstance(context.channel, discord.DMChannel):
        data['channel_id'] = context.channel.id

    data_as_file = io.StringIO(json.dumps(data))
    job = client.load_table_from_file(data_as_file, 'formal-scout-290305.analytics.commands', job_config=job_config)

    try:
        job.result()  # Waits for the job to complete.
    except Exception as e:
        raise Exception(f'Failed BigQuery upload job. Exception: {e} Errors: {job.errors}')


def log_command(command_name: str, is_slash: bool, context: Union[commands.Context, SlashContext]):
    threading.Thread(target=_log_command, args=(command_name, is_slash, context)).start()

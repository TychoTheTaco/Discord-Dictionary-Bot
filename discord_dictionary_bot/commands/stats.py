from discord_slash import SlashContext
from google.cloud import bigquery

from .command import Command, Context
from .. import utils
from ..discord_bot_client import DiscordBotClient


class StatsCommand(Command):

    def __init__(self, client: DiscordBotClient):
        super().__init__(client, 'stats', description='Shows you some stats about this bot.')
        self._bigquery_client = bigquery.Client()

    async def execute(self, context: Context, args: tuple) -> None:
        reply = '**----- Statistics -----**\n'

        # Channel count
        channel_count_job = self._bigquery_client.query('SELECT COUNT(DISTINCT(channel_id)) AS uniqueChannels FROM definition_requests.definition_requests')
        channel_count_results = channel_count_job.result()
        for row in channel_count_results:
            channel_count = row.uniqueChannels

        # Guild count
        reply += '**Guilds**\n'
        reply += f'Active in **{len(self.client.guilds)}** guilds and **{channel_count}** channels.\n\n'

        # Total requests
        reply += '**Total Requests**\n'
        total_requests_job = self._bigquery_client.query('SELECT COUNT(*) AS total FROM definition_requests.definition_requests')
        total_requests_results = total_requests_job.result()
        for row in total_requests_results:
            total_requests = row.total
        reply += f'**{total_requests}** requests.\n\n'

        # Most common words
        reply += '**Most Common Words**\n'
        top_5_words_job = self._bigquery_client.query('SELECT word, COUNT(word) AS count, MAX(time) as time FROM definition_requests.definition_requests GROUP BY word HAVING count > 1 ORDER BY count DESC, time DESC LIMIT 5')
        top_5_words_results = top_5_words_job.result()
        for i, row in enumerate(top_5_words_results):
            reply += f'{i + 1}. `{row.word}` ({row.count})\n'

        # Most recent words
        reply += '\n**Most Recent Words**\n'
        job = self._bigquery_client.query('SELECT word, MAX(time) as time FROM definition_requests.definition_requests GROUP BY word ORDER BY time DESC LIMIT 3')
        results = job.result()
        for i, row in enumerate(results):
            reply += f'{i + 1}. `{row.word}`\n'

        await utils.send_split(reply, context.channel)

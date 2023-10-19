import logging

from discord import app_commands, Interaction
from discord.ext.commands import Cog, Bot
from google.cloud import bigquery

# Set up logging
logger = logging.getLogger(__name__)


class Statistics(Cog):

    def __init__(self, bot: Bot):
        super().__init__()
        self._bot = bot
        self._bigquery_client = bigquery.Client()

    @app_commands.command(name='stats', description='Shows some statistics about the bot.')
    async def stats(self, interaction: Interaction):
        await interaction.response.defer(ephemeral=True)
        reply = '**----- Statistics -----**\n'

        # Channel count
        channel_count_job = self._bigquery_client.query('SELECT COUNT(DISTINCT(channel_id)) AS uniqueChannels FROM analytics.definition_requests')
        channel_count_results = channel_count_job.result()
        for row in channel_count_results:
            channel_count = row.uniqueChannels

        # Guild count
        reply += '**Guilds**\n'
        reply += f'Active in **{len(self._bot.guilds):,}** guilds and **{channel_count:,}** channels.\n\n'

        # Total requests
        reply += '**Total Requests**\n'
        total_requests_job = self._bigquery_client.query('SELECT COUNT(*) AS total FROM analytics.definition_requests')
        total_requests_results = total_requests_job.result()
        for row in total_requests_results:
            total_requests = row.total
        reply += f'**{total_requests:,}** requests.\n\n'

        # Most common words
        reply += '**Most Common Words**\n'
        top_5_words_job = self._bigquery_client.query(
            'SELECT word, COUNT(word) AS count, MAX(time) as time FROM analytics.definition_requests GROUP BY word HAVING count > 1 ORDER BY count DESC, time DESC LIMIT 5')
        top_5_words_results = top_5_words_job.result()
        for i, row in enumerate(top_5_words_results):
            reply += f'{i + 1}. `{row.word}` ({row.count})\n'

        # Most recent words
        reply += '\n**Most Recent Words**\n'
        job = self._bigquery_client.query('SELECT word, MAX(time) as time FROM analytics.definition_requests GROUP BY word ORDER BY time DESC LIMIT 3')
        results = job.result()
        for i, row in enumerate(results):
            reply += f'{i + 1}. `{row.word}`\n'

        await interaction.followup.send(reply)

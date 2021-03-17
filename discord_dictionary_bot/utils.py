import logging
from typing import Union, Optional

from discord.ext import commands
from discord_slash import SlashContext

# Set up logging
logger = logging.getLogger(__name__)


async def send_maybe_hidden(context: Union[commands.Context, SlashContext], text: Optional[str] = None, **kwargs):
    if isinstance(context, SlashContext):
        return await context.send(text, hidden=True, **kwargs)
    return await context.send(text, **kwargs)

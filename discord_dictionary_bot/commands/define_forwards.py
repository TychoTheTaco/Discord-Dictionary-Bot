from .define import DefineCommand
from ..discord_bot_client import DiscordBotClient
from .command import Context


class DefineForwardsCommand(DefineCommand):

    def __init__(self, client: DiscordBotClient, definition_response_manager):
        super().__init__(client, definition_response_manager, 'define', aliases=['d'], description='Gets the definition of a word and optionally reads it out to you.')

        @client.slash_command_decorator.slash(name="define", guild_ids=[454852632528420876], options=[
            {
                'name': 'word',
                'description': 'The word to define.',
                'type': 3,
                'required': True
            },
            {
                'name': 'text_to_speech',
                'description': 'Reads the definition to you.',
                'type': 5
            },
            {
                'name': 'language',
                'description': 'The language to use when reading the definition.',
                'type': 3,
            }
        ])
        async def _on_slash_command(slash_context, *args):
            if isinstance(slash_context.author, int):
                slash_context.author = await client.fetch_user(slash_context.author)
            if isinstance(slash_context.channel, int):
                slash_context.channel = await client.fetch_user(slash_context.channel)

            context = Context(slash_context.author, slash_context.channel)
            print(args)
            self.execute(context, args)

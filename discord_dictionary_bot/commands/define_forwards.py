from .define import DefineCommand
from ..discord_bot_client import DiscordBotClient
from .command import Context


class DefineForwardsCommand(DefineCommand):

    def __init__(self, client: DiscordBotClient, definition_response_manager):
        super().__init__(
            client,
            definition_response_manager,
            'define',
            aliases=['d'],
            description='Gets the definition of a word and optionally reads it out to you.',
            slash_command_options=[
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

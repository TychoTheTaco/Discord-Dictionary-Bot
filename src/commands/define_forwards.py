from commands.define import DefineCommand
import discord


class DefineForwardsCommand(DefineCommand):

    def __init__(self, client: discord.Client, definition_response_manager):
        super().__init__(client, definition_response_manager, 'define', aliases=['d'], description='Gets the definition of a word and optionally reads it out to you.')

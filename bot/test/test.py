import unittest

from discord_dictionary_bot.discord_bot_client import interaction_data_to_string


class TestDiscordBotClient(unittest.TestCase):

    def test_interaction_data_to_string(self):
        cases = [
            ({'type': 1, 'name': 'stats', 'id': '1024755836851060826', 'guild_id': '799455809297842177'}, "stats"),
            ({'type': 1, 'options': [{'value': 'water', 'type': 3, 'name': 'word'}], 'name': 'define', 'id': '1024788224998133821', 'guild_id': '799455809297842177'}, "define {'word': 'water'}"),
            ({'type': 1, 'options': [{'type': 1, 'options': [{'value': 'all', 'type': 3, 'name': 'scope_name'}], 'name': 'list'}], 'name': 'settings', 'id': '1024788805225562143', 'guild_id': '799455809297842177'},
             "settings list {'scope_name': 'all'}"),
            ({'type': 1, 'options': [{'value': 'chick', 'type': 3, 'name': 'word'}, {'value': False, 'type': 5, 'name': 'text_to_speech'}, {'value': 'en', 'type': 3, 'name': 'language'}], 'name': 'define', 'id': '1024788224998133821',
              'guild_id': '799455809297842177'}, "define {'word': 'chick', 'text_to_speech': False, 'language': 'en'}"),
        ]
        for data, expected in cases:
            self.assertEqual(interaction_data_to_string(data), expected)


if __name__ == '__main__':
    unittest.main()

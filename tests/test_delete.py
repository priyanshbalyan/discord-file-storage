import argparse
import unittest
from unittest.mock import patch

from discord_fs.commands.delete import delete_file
from discord_fs.utils import encode


class TestDeleteCommand(unittest.TestCase):
    @patch("discord_fs.commands.delete.update_file_index")
    @patch("discord_fs.commands.delete.get_file_index")
    @patch("discord_fs.commands.delete.load_file_index", return_value="index")
    @patch("discord_fs.commands.delete.DiscordClient")
    @patch("discord_fs.commands.delete.tqdm")
    def test_handles_unexpected_chunk_error(self, progress, client, _load, index, _update):
        name = encode("old.txt")
        index.return_value = {name: {"filename": name, "urls": [["m", "a"]]}}
        client.side_effect = RuntimeError("surprise")
        delete_file(argparse.Namespace(id=["1"]))
        progress.return_value.close.assert_called_once()

    @patch("discord_fs.commands.delete.update_file_index")
    @patch("discord_fs.commands.delete.get_file_index")
    @patch("discord_fs.commands.delete.load_file_index", return_value="index")
    @patch("discord_fs.commands.delete.DiscordClient")
    @patch("discord_fs.commands.delete.tqdm")
    def test_tolerates_entry_disappearing_from_index(self, _progress, _client, _load, get_index, update):
        name = encode("old.txt")

        class VanishingIndex(dict):
            def __contains__(self, key):
                return False

        index = VanishingIndex({name: {"filename": name, "urls": []}})
        get_index.return_value = index
        delete_file(argparse.Namespace(id=["1"]))
        update.assert_called_once_with("index", index)

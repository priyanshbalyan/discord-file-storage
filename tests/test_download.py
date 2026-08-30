import argparse
import unittest
from unittest.mock import patch

from discord_fs.commands.download import download_file
from discord_fs.utils import encode


class TestDownloadCommand(unittest.TestCase):
    @patch("builtins.print")
    def test_rejects_malformed_id(self, printed):
        download_file(argparse.Namespace(id=["bad"]))
        printed.assert_called_with("Invalid ID format: bad")

    @patch("discord_fs.commands.download.load_file_index", side_effect=RuntimeError("offline"))
    def test_handles_index_error(self, _load):
        download_file(argparse.Namespace(id=["1"]))

    @patch("discord_fs.commands.download.DiscordClient")
    @patch("discord_fs.commands.download.get_file_index", return_value={})
    @patch("discord_fs.commands.download.load_file_index")
    def test_skips_out_of_range_ids(self, _load, _index, client):
        download_file(argparse.Namespace(id=["0", "2"]))
        client.return_value.get_message.assert_not_called()

    def _download_with_open_error(self, error):
        name = encode("file.txt")
        index = {name: {"filename": name, "urls": []}}
        with (
            patch("discord_fs.commands.download.load_file_index"),
            patch("discord_fs.commands.download.get_file_index", return_value=index),
            patch("discord_fs.commands.download.os.makedirs"),
            patch("builtins.open", side_effect=error),
        ):
            download_file(argparse.Namespace(id=["1"]))

    def test_handles_io_error(self):
        self._download_with_open_error(IOError("disk full"))

    def test_handles_unexpected_error(self):
        self._download_with_open_error(RuntimeError("surprise"))

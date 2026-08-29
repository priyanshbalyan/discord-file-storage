import argparse
import unittest
from unittest.mock import MagicMock, patch

import httpx

from discord_fs.commands.delete import delete_file
from discord_fs.commands.find import find_file
from discord_fs.commands.rename import rename_file
from discord_fs.utils import encode


class TestFindCommand(unittest.TestCase):
    @patch("discord_fs.commands.find.print_table_row")
    @patch("discord_fs.commands.find.print_table_header", return_value=("fmt", 40))
    @patch("discord_fs.commands.find.get_file_index")
    @patch("discord_fs.commands.find.load_file_index")
    def test_find_matches_case_insensitively(
        self, mock_load, mock_index, mock_header, mock_row
    ):
        mock_index.return_value = {
            "one": {"filename": encode("Holiday Photo.jpg"), "size": 12},
            "two": {"filename": encode("notes.txt"), "size": 4},
        }

        find_file(argparse.Namespace(query=["HOLIDAY", "photo"]))

        mock_load.assert_called_once_with()
        mock_header.assert_called_once_with()
        mock_row.assert_called_once_with(1, "holiday photo.jpg", 12, "fmt", 40)

    @patch("builtins.print")
    @patch("discord_fs.commands.find.get_file_index", return_value={})
    @patch("discord_fs.commands.find.load_file_index")
    def test_find_reports_no_matches(self, mock_load, mock_index, mock_print):
        find_file(argparse.Namespace(query=["missing"]))
        mock_print.assert_called_once_with("No matching files found in the server.")


class TestRenameCommand(unittest.TestCase):
    @patch("builtins.print")
    def test_rename_rejects_malformed_id(self, mock_print):
        rename_file(argparse.Namespace(id="#bad"))
        mock_print.assert_called_once_with("Invalid ID format")

    @patch("builtins.print")
    @patch("discord_fs.commands.rename.get_file_index", return_value={})
    @patch("discord_fs.commands.rename.load_file_index", return_value="index-id")
    def test_rename_rejects_out_of_range_id(self, mock_load, mock_index, mock_print):
        rename_file(argparse.Namespace(id="1"))
        mock_print.assert_called_with("Invalid ID provided")

    @patch("builtins.input", return_value="new name.txt")
    @patch("discord_fs.commands.rename.update_file_index")
    @patch("discord_fs.commands.rename.get_file_index")
    @patch("discord_fs.commands.rename.load_file_index", return_value="index-id")
    def test_rename_updates_entry(
        self, mock_load, mock_index, mock_update, mock_input
    ):
        old_name = encode("old.txt")
        index = {
            old_name: {
                "filename": old_name,
                "size": 1024,
                "urls": [["message", "attachment"]],
            }
        }
        mock_index.return_value = index

        rename_file(argparse.Namespace(id="#1"))

        self.assertEqual(index[old_name]["filename"], encode("new name.txt"))
        mock_update.assert_called_once_with("index-id", index)


class TestDeleteCommand(unittest.TestCase):
    @patch("builtins.print")
    @patch("discord_fs.commands.delete.load_file_index", return_value=None)
    def test_delete_stops_without_server_index(self, mock_load, mock_print):
        delete_file(argparse.Namespace(id=["1"]))
        mock_print.assert_called_with("No index file found on server.")

    @patch("builtins.print")
    @patch("discord_fs.commands.delete.load_file_index", side_effect=RuntimeError("offline"))
    def test_delete_handles_index_error(self, mock_load, mock_print):
        delete_file(argparse.Namespace(id=["1"]))
        mock_print.assert_called_with("Error loading file index: offline")

    @patch("discord_fs.commands.delete.update_file_index")
    @patch("discord_fs.commands.delete.get_file_index")
    @patch("discord_fs.commands.delete.load_file_index", return_value="index-id")
    @patch("discord_fs.commands.delete.DiscordClient")
    @patch("discord_fs.commands.delete.tqdm")
    def test_delete_valid_file(
        self, mock_tqdm, mock_client, mock_load, mock_index, mock_update
    ):
        name = encode("old.txt")
        index = {name: {"filename": name, "urls": [["m1", "a1"], ["m2", "a2"]]}}
        mock_index.return_value = index

        delete_file(argparse.Namespace(id=["bad", "9", "#1"]))

        self.assertEqual(mock_client.return_value.delete_message.call_count, 2)
        self.assertEqual(index, {})
        mock_update.assert_called_once_with("index-id", index)

    @patch("discord_fs.commands.delete.update_file_index")
    @patch("discord_fs.commands.delete.get_file_index")
    @patch("discord_fs.commands.delete.load_file_index", return_value="index-id")
    @patch("discord_fs.commands.delete.DiscordClient")
    @patch("discord_fs.commands.delete.tqdm")
    def test_delete_handles_http_error(
        self, mock_tqdm, mock_client, mock_load, mock_index, mock_update
    ):
        name = encode("old.txt")
        index = {name: {"filename": name, "urls": [["m1", "a1"]]}}
        mock_index.return_value = index
        response = MagicMock(status_code=500, text="failed")
        mock_client.return_value.delete_message.side_effect = httpx.HTTPStatusError(
            "failed", request=MagicMock(), response=response
        )

        delete_file(argparse.Namespace(id=["1"]))

        mock_tqdm.return_value.close.assert_called()
        mock_update.assert_called_once_with("index-id", {})

    @patch("builtins.print")
    @patch("discord_fs.commands.delete.update_file_index", side_effect=RuntimeError("failed"))
    @patch("discord_fs.commands.delete.get_file_index", return_value={})
    @patch("discord_fs.commands.delete.load_file_index", return_value="index-id")
    def test_delete_reports_index_update_error(
        self, mock_load, mock_index, mock_update, mock_print
    ):
        delete_file(argparse.Namespace(id=[]))
        mock_print.assert_called_with("Error updating file index after deletion: failed")


if __name__ == "__main__":
    unittest.main()

import argparse
import unittest
from unittest.mock import patch

from discord_fs.commands.list import list_files
from discord_fs.utils import encode


class TestListFiles(unittest.TestCase):
    @patch("builtins.print")
    @patch("discord_fs.commands.list.load_file_index")
    @patch("discord_fs.commands.list.get_file_index")
    def test_list_marks_partial_uploads(self, mock_get_index, mock_load_index, mock_print):
        mock_get_index.return_value = {
            encode("test.txt"): {
                "filename": encode("test.txt"),
                "size": 100,
                "urls": [["msg1", "att1"]],
                "is_partial": True,
            }
        }

        list_files(argparse.Namespace())

        printed_lines = [call.args[0] for call in mock_print.call_args_list if call.args]
        self.assertTrue(any("test.txt (partial)" in line for line in printed_lines))

    @patch("discord_fs.commands.list.print_table_row")
    @patch("discord_fs.commands.list.load_file_index")
    @patch("discord_fs.commands.list.get_file_index")
    def test_list_keeps_complete_filename_unchanged(self, mock_get_index, _load, row):
        mock_get_index.return_value = {
            "name": {"filename": encode("complete.txt"), "size": 1, "urls": []}
        }
        list_files(argparse.Namespace())
        self.assertEqual(row.call_args.args[1], "complete.txt")


if __name__ == "__main__":
    unittest.main()

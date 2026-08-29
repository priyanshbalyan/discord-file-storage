import argparse
import os
import unittest
from unittest.mock import mock_open, patch

from discord_fs import config, main, utils


class TestConfig(unittest.TestCase):
    def setUp(self):
        self.previous = (config.TOKEN, config.CHANNEL_ID, config.HEADERS, config.CDN_BASE_URL)
        config.TOKEN = ""
        config.CHANNEL_ID = ""
        config.HEADERS = {}
        config.CDN_BASE_URL = ""

    def tearDown(self):
        config.TOKEN, config.CHANNEL_ID, config.HEADERS, config.CDN_BASE_URL = self.previous

    @patch("builtins.open", new_callable=mock_open, read_data="TOKEN=abc\nCHANNEL_ID=123\n")
    def test_load_config(self, mock_file):
        config.load_config()
        self.assertEqual(config.TOKEN, "abc")
        self.assertEqual(config.CHANNEL_ID, "123")
        self.assertEqual(config.HEADERS, {"Authorization": "Bot abc"})
        self.assertTrue(config.CDN_BASE_URL.endswith("/123/"))

    @patch("builtins.open", side_effect=FileNotFoundError)
    def test_load_config_without_file(self, mock_file):
        config.load_config()
        self.assertEqual(config.HEADERS, {})

    @patch("builtins.open", new_callable=mock_open)
    def test_save_config(self, mock_file):
        config.save_config("token", "channel")
        mock_file().write.assert_called_once_with("TOKEN=token\nCHANNEL_ID=channel")
        self.assertEqual(config.HEADERS["Authorization"], "Bot token")


class TestUtils(unittest.TestCase):
    @patch("discord_fs.utils.os.get_terminal_size", side_effect=OSError)
    def test_terminal_size_fallback_and_header(self, mock_size):
        self.assertEqual(utils.get_terminal_size(), os.terminal_size((80, 24)))
        formatting, width = utils.print_table_header()
        self.assertEqual(width, 58)
        self.assertIn("%-58s", formatting)

    @patch("builtins.print")
    def test_print_table_row_wraps_long_filename(self, mock_print):
        utils.print_table_row(2, "abcdefgh", 10, "%-5s %-5s %-5s", 5)
        self.assertEqual(mock_print.call_count, 2)

    @patch("discord_fs.utils.get_terminal_size", return_value=os.terminal_size((80, 24)))
    @patch("builtins.print")
    def test_progress_bar_completion(self, mock_print, mock_size):
        utils.show_progress_bar(2, 2)
        self.assertEqual(mock_print.call_count, 2)

    @patch("discord_fs.utils.time.sleep")
    def test_with_retry_callback(self, mock_sleep):
        attempts = []

        def operation():
            if not attempts:
                attempts.append("failed")
                raise ValueError("try again")
            return "ok"

        retries = []
        self.assertEqual(
            utils.with_retry(operation, delay=0.1, on_retry=lambda n, e: retries.append(n)),
            "ok",
        )
        self.assertEqual(retries, [1])


class TestMain(unittest.TestCase):
    @patch("discord_fs.main.load_config")
    @patch.object(config, "TOKEN", "token")
    @patch.object(config, "CHANNEL_ID", "channel")
    @patch("discord_fs.main.list_files")
    @patch("sys.argv", ["fs.py", "-l"])
    def test_legacy_list_dispatches(self, mock_list, mock_load):
        main.init()
        mock_list.assert_called_once()

    @patch("discord_fs.main.load_config")
    @patch.object(config, "TOKEN", "token")
    @patch.object(config, "CHANNEL_ID", "channel")
    @patch("sys.argv", ["fs.py"])
    def test_no_command_exits(self, mock_load):
        with self.assertRaises(SystemExit) as raised:
            main.init()
        self.assertEqual(raised.exception.code, 1)

    @patch("discord_fs.main.load_config")
    @patch("discord_fs.main.save_config")
    @patch.object(config, "TOKEN", "")
    @patch.object(config, "CHANNEL_ID", "")
    @patch("builtins.input", side_effect=["token", "channel"])
    @patch("sys.argv", ["fs.py", "list"])
    @patch("discord_fs.main.list_files")
    def test_missing_config_prompts(
        self, mock_list, mock_input, mock_save, mock_load
    ):
        main.init()
        mock_save.assert_called_once_with("token", "channel")
        self.assertEqual(mock_load.call_count, 2)

    @patch("builtins.print")
    @patch("discord_fs.main.load_config")
    @patch.object(config, "TOKEN", "token")
    @patch.object(config, "CHANNEL_ID", "channel")
    @patch("discord_fs.main.list_files", side_effect=RuntimeError("boom"))
    @patch("sys.argv", ["fs.py", "list"])
    def test_command_errors_are_reported(self, mock_list, mock_load, mock_print):
        main.init()
        mock_print.assert_called_with("An error occurred: boom")


if __name__ == "__main__":
    unittest.main()

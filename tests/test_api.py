import unittest
from unittest.mock import MagicMock, mock_open, patch

import httpx

from discord_fs import api


def status_error(status=500, text="failed"):
    response = MagicMock(status_code=status, text=text)
    return httpx.HTTPStatusError(text, request=MagicMock(), response=response)


class TestApi(unittest.TestCase):
    @patch("discord_fs.api.DiscordClient")
    def test_load_index_http_error(self, client):
        client.return_value.get_messages.side_effect = status_error(503, "offline")
        with self.assertRaisesRegex(api.APIError, "503 offline"):
            api.load_file_index()

    @patch("discord_fs.api.DiscordClient")
    def test_load_index_empty_messages(self, client):
        client.return_value.get_messages.return_value.json.return_value = []
        self.assertIsNone(api.load_file_index())

    @patch("builtins.open", side_effect=FileNotFoundError)
    def test_get_index_missing(self, _open):
        self.assertEqual(api.get_file_index(), {})

    @patch("builtins.open", new_callable=mock_open)
    def test_save_index_locally(self, opened):
        api.save_file_index_locally({"a": 1})
        opened().write.assert_called_once_with('{"a": 1}')

    @patch("builtins.open", new_callable=mock_open)
    @patch("discord_fs.api.DiscordClient")
    def test_update_index_continues_when_old_index_deletion_fails(self, client, _open):
        client.return_value.delete_message.side_effect = status_error()
        client.return_value.post_message.return_value.json.return_value = {"id": "new"}
        self.assertEqual(api.update_file_index("old", {}), "new")

    @patch("builtins.open", new_callable=mock_open)
    @patch("discord_fs.api.DiscordClient")
    def test_update_index_upload_error(self, client, _open):
        client.return_value.post_message.side_effect = status_error(500, "nope")
        with self.assertRaisesRegex(api.APIError, "nope"):
            api.update_file_index(None, {})

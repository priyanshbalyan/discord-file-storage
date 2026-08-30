import unittest
from unittest.mock import MagicMock, mock_open, patch

import httpx

from discord_fs import api


class TestLoadFileIndex(unittest.TestCase):
    @patch("discord_fs.api.DiscordClient")
    def test_load_file_index_wraps_http_errors(self, MockClient):
        response = MagicMock(status_code=503, text="unavailable")
        MockClient.return_value.get_messages.side_effect = httpx.HTTPStatusError(
            "failed", request=MagicMock(), response=response
        )

        with self.assertRaisesRegex(api.APIError, "503 unavailable"):
            api.load_file_index()

    @patch("builtins.print")
    @patch("discord_fs.api.DiscordClient")
    def test_load_file_index_handles_empty_message_list(self, MockClient, mock_print):
        MockClient.return_value.get_messages.return_value.json.return_value = []

        self.assertIsNone(api.load_file_index())

        mock_print.assert_called_once_with("No index file found")

    @patch("builtins.open", new_callable=mock_open)
    @patch("discord_fs.api.DiscordClient")
    def test_load_file_index_skips_messages_without_attachments(self, MockClient, mock_file):
        client = MockClient.return_value
        messages_response = MagicMock()
        messages_response.json.return_value = [
            {"id": "latest", "attachments": []},
            {
                "id": "index-message",
                "attachments": [
                    {"filename": "index.txt", "url": "https://example.com/index.txt"}
                ],
            },
        ]
        index_response = MagicMock()
        index_response.text = '{"file": "index"}'
        client.get_messages.return_value = messages_response
        client.download_file.return_value = index_response

        message_id = api.load_file_index()

        self.assertEqual(message_id, "index-message")
        client.get_messages.assert_called_once_with(limit=100)
        client.download_file.assert_called_once_with("https://example.com/index.txt")
        mock_file().write.assert_called_once_with('{"file": "index"}')

    @patch("builtins.open", new_callable=mock_open)
    @patch("discord_fs.api.DiscordClient")
    def test_load_file_index_returns_none_when_no_index_attachment(self, MockClient, mock_file):
        client = MockClient.return_value
        messages_response = MagicMock()
        messages_response.json.return_value = [
            {"id": "latest"},
            {
                "id": "chunk-message",
                "attachments": [
                    {"filename": "file.txt.0", "url": "https://example.com/file.txt.0"}
                ],
            },
        ]
        client.get_messages.return_value = messages_response

        message_id = api.load_file_index()

        self.assertIsNone(message_id)
        client.get_messages.assert_called_once_with(limit=100)
        client.download_file.assert_not_called()
        mock_file.assert_not_called()


class TestFileIndex(unittest.TestCase):
    @patch("builtins.open", side_effect=FileNotFoundError)
    def test_get_file_index_returns_empty_dict_when_missing(self, mock_file):
        self.assertEqual(api.get_file_index(), {})

    @patch("builtins.open", new_callable=mock_open)
    @patch("discord_fs.api.DiscordClient")
    def test_update_file_index_continues_after_delete_error(self, MockClient, mock_file):
        client = MockClient.return_value
        response = MagicMock(status_code=500, text="failed")
        client.delete_message.side_effect = httpx.HTTPStatusError(
            "failed", request=MagicMock(), response=response
        )
        client.post_message.return_value.json.return_value = {"id": "new-index"}

        self.assertEqual(api.update_file_index("old-index", {"file": "data"}), "new-index")

        client.delete_message.assert_called_once_with("old-index")
        client.post_message.assert_called_once()

    @patch("builtins.open", new_callable=mock_open)
    @patch("discord_fs.api.DiscordClient")
    def test_update_file_index_wraps_upload_error(self, MockClient, mock_file):
        response = MagicMock(status_code=500, text="upload failed")
        MockClient.return_value.post_message.side_effect = httpx.HTTPStatusError(
            "failed", request=MagicMock(), response=response
        )

        with self.assertRaisesRegex(api.APIError, "upload failed"):
            api.update_file_index(None, {"file": "data"})


if __name__ == "__main__":
    unittest.main()

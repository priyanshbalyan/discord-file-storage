import unittest
from unittest.mock import MagicMock, mock_open, patch

from discord_fs import api


class TestLoadFileIndex(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()

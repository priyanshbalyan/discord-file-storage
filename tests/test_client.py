import io
import unittest
from unittest.mock import MagicMock, patch

from discord_fs.client import DiscordClient


class TestDiscordClient(unittest.TestCase):
    @patch("discord_fs.client.with_retry")
    def test_retry_callback_rewinds_valid_files_and_ignores_bad_shapes(self, retry):
        callback = MagicMock()
        seekable = io.BytesIO(b"abc")
        files = [("", ("name", seekable)), ("bad",), None]
        DiscordClient()._make_request("POST", "url", files=files, on_retry=callback)
        internal_callback = retry.call_args.kwargs["on_retry"]
        seekable.read()
        internal_callback(2, ValueError("again"))
        self.assertEqual(seekable.tell(), 0)
        callback.assert_called_once()

    @patch("discord_fs.client.with_retry")
    def test_retry_callback_without_files_or_external_callback(self, retry):
        DiscordClient()._make_request("GET", "url")
        retry.call_args.kwargs["on_retry"](1, ValueError())

    @patch("discord_fs.client.with_retry")
    def test_retry_callback_leaves_non_seekable_file_alone(self, retry):
        DiscordClient()._make_request("POST", "url", files=[("", ("name", object()))])
        retry.call_args.kwargs["on_retry"](1, ValueError())

    @patch.object(DiscordClient, "_make_request")
    def test_request_helpers(self, request):
        client = DiscordClient()
        client.get_messages(3)
        client.post_message([])
        client.delete_message("42")
        client.download_file("cdn")
        self.assertEqual(request.call_count, 4)

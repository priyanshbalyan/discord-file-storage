import argparse
import unittest
from unittest.mock import MagicMock, mock_open, patch

from discord_fs.commands.upload import upload_file
from discord_fs.utils import encode


class TestUploadCommand(unittest.TestCase):
    @patch("builtins.open", side_effect=FileNotFoundError("missing"))
    @patch("discord_fs.commands.upload.load_file_index")
    def test_missing_file(self, _load, _open):
        upload_file(argparse.Namespace(file="missing"))

    @patch("discord_fs.commands.upload.load_file_index", side_effect=RuntimeError("offline"))
    def test_index_error(self, _load):
        upload_file(argparse.Namespace(file="file"))

    @patch("builtins.open", new_callable=mock_open, read_data=b"abc")
    @patch("discord_fs.commands.upload.os.path.getsize", return_value=3)
    @patch("discord_fs.commands.upload.get_file_index")
    @patch("discord_fs.commands.upload.load_file_index")
    def test_already_complete(self, _load, index, _size, _open):
        name = encode("file")
        index.return_value = {name: {"filename": name, "urls": []}}
        upload_file(argparse.Namespace(file="file"))

    def _run_upload(self, *, request_side_effect=None, read_data=b"abc", signal_error=None):
        response = MagicMock()
        response.json.return_value = {"id": "m", "attachments": [{"id": "a"}]}
        with (
            patch("builtins.open", new_callable=mock_open, read_data=read_data),
            patch("discord_fs.commands.upload.os.path.getsize", return_value=3),
            patch("discord_fs.commands.upload.load_file_index", return_value="index"),
            patch("discord_fs.commands.upload.get_file_index", return_value={}),
            patch("discord_fs.commands.upload.update_file_index"),
            patch("discord_fs.commands.upload.save_file_index_locally"),
            patch("discord_fs.commands.upload.get_total_chunks", return_value=1),
            patch("discord_fs.commands.upload.DiscordClient") as client,
            patch("discord_fs.commands.upload.tqdm") as progress,
            patch("discord_fs.commands.upload.signal.signal", side_effect=signal_error),
        ):
            client.return_value._make_request.side_effect = request_side_effect
            if request_side_effect is None:
                client.return_value._make_request.return_value = response
            upload_file(argparse.Namespace(file="file"))
            return client, progress

    def test_works_when_signal_handler_cannot_be_installed(self):
        self._run_upload(signal_error=ValueError("not main thread"))

    def test_stops_on_empty_read(self):
        self._run_upload(read_data=b"")

    def test_reports_non_http_chunk_error_and_invokes_retry_callback(self):
        def fail(*args, **kwargs):
            kwargs["on_retry"](1, ValueError("first"))
            raise RuntimeError("failed")

        _client, progress = self._run_upload(request_side_effect=fail)
        progress.return_value.write.assert_called_once()

    def test_handles_keyboard_interrupt(self):
        self._run_upload(request_side_effect=KeyboardInterrupt)

    def test_handles_unexpected_post_response_error(self):
        response = MagicMock()
        response.json.return_value = {"id": "m", "attachments": [{"id": "a"}]}
        with (
            patch("builtins.open", new_callable=mock_open, read_data=b"abc"),
            patch("discord_fs.commands.upload.os.path.getsize", return_value=3),
            patch("discord_fs.commands.upload.load_file_index", return_value="index"),
            patch("discord_fs.commands.upload.get_file_index", return_value={}),
            patch("discord_fs.commands.upload.update_file_index"),
            patch("discord_fs.commands.upload.save_file_index_locally"),
            patch("discord_fs.commands.upload.get_total_chunks", return_value=1),
            patch("discord_fs.commands.upload.DiscordClient") as client,
            patch("discord_fs.commands.upload.tqdm") as progress,
        ):
            client.return_value._make_request.return_value = response
            progress.return_value.update.side_effect = RuntimeError("progress failed")
            upload_file(argparse.Namespace(file="file"))

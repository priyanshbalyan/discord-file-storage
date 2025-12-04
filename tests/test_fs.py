import sys
from unittest.mock import MagicMock
import argparse

# Mock httpx module before importing fs
# Mock httpx module before importing fs
mock_httpx = MagicMock()
class MockHTTPStatusError(Exception):
    def __init__(self, message, *, request, response):
        self.response = response
        super().__init__(message)
mock_httpx.HTTPStatusError = MockHTTPStatusError
sys.modules["httpx"] = mock_httpx
import httpx

import unittest
from unittest.mock import patch, mock_open
import os
import json
from discord_fs import utils, api, commands

class TestFS(unittest.TestCase):

    def test_get_size_format(self):
        self.assertEqual(utils.get_size_format(100), "100.00 B")
        self.assertEqual(utils.get_size_format(1025), "1.00 KB")
        self.assertEqual(utils.get_size_format(1024 * 1024 + 1), "1.00 MB")

    def test_encode_decode(self):
        original = "Hello World"
        encoded = utils.encode(original)
        decoded = utils.decode(encoded)
        self.assertEqual(decoded, original)
        self.assertNotEqual(encoded, original)
        
        # Test with special characters
        special = "Hello_World!123"
        self.assertEqual(utils.decode(utils.encode(special)), special)

    def test_get_total_chunks(self):
        # CHUNK_SIZE is 8MB
        self.assertEqual(utils.get_total_chunks(100), 1)
        self.assertEqual(utils.get_total_chunks(8 * 1000 * 1000), 1)
        self.assertEqual(utils.get_total_chunks(8 * 1000 * 1000 + 1), 2)

    @patch('discord_fs.client.httpx.request')
    @patch('builtins.open', new_callable=mock_open)
    def test_load_file_index_success(self, mock_file, mock_request):
        # Mock response for finding the index file message
        mock_response_list = MagicMock()
        mock_response_list.status_code = 200
        mock_response_list.json.return_value = [{
            "id": "12345",
            "attachments": [{
                "filename": "index.txt",
                "url": "http://example.com/index.txt"
            }]
        }]
        
        # Mock response for downloading the index file content
        mock_response_file = MagicMock()
        mock_response_file.text = '{"test": "data"}'
        
        mock_request.side_effect = [mock_response_list, mock_response_file]
        
        message_id = api.load_file_index()
        
        self.assertEqual(message_id, "12345")
        mock_file.assert_called_with("index.txt", "w")
        mock_file().write.assert_called_with('{"test": "data"}')

    @patch('builtins.open', new_callable=mock_open, read_data='{"test": "data"}')
    def test_get_file_index(self, mock_file):
        index = api.get_file_index()
        self.assertEqual(index, {"test": "data"})

    @patch('os.get_terminal_size')
    @patch('discord_fs.client.httpx.request')
    @patch('discord_fs.commands.upload.load_file_index')
    @patch('discord_fs.commands.upload.get_file_index')
    @patch('discord_fs.commands.upload.update_file_index')
    @patch('os.path.getsize')
    @patch('builtins.open', new_callable=mock_open, read_data=b'some data')
    def test_upload_file(self, mock_file, mock_getsize, mock_update, mock_get_index, mock_load, mock_request, mock_terminal_size):
        # Setup mocks
        mock_terminal_size.return_value = (80, 24)
        mock_load.return_value = "old_msg_id"
        mock_get_index.return_value = {}
        mock_getsize.return_value = 100
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "new_msg_id",
            "attachments": [{"id": "att_id"}]
        }
        mock_request.return_value = mock_response
        
        # Run upload
        # Note: upload_file is now in discord_fs.commands.upload
        # Pass argparse.Namespace
        args = argparse.Namespace(file="test_file.txt")
        commands.upload_file(args)
        
        # Verify
        self.assertTrue(mock_request.called)
        self.assertTrue(mock_update.called)
        
        # Check if file index was updated correctly in the call to update_file_index
        args, _ = mock_update.call_args
        updated_index = args[1]
        encoded_name = utils.encode("test_file.txt")
        self.assertIn(encoded_name, updated_index)
        self.assertEqual(updated_index[encoded_name]['size'], 100)
        
        # Verify files argument structure
        # mock_request is called with (method, url, headers=..., files=...)
        # We want to check the 'files' kwarg of the last call (or any call)
        _, kwargs = mock_request.call_args
        files = kwargs.get('files')
        self.assertIsNotNone(files)
        self.assertIsInstance(files, list)
        self.assertTrue(len(files) > 0)
        # Check that the inner item is a tuple, not a list
        # files = [("", (filename, chunk))]
        self.assertIsInstance(files[0], tuple)
        self.assertEqual(len(files[0]), 2)
        self.assertIsInstance(files[0][1], tuple)

    @patch('discord_fs.client.httpx.request')
    @patch('builtins.open', new_callable=mock_open)
    def test_update_file_index(self, mock_file, mock_request):
        # Setup mock
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_request.return_value = mock_response
        
        # Call update_file_index
        api.update_file_index(None, {"test": "data"})
        
        # Verify files argument structure
        self.assertTrue(mock_request.called)
        _, kwargs = mock_request.call_args
        files = kwargs.get('files')
        
        self.assertIsNotNone(files)
        self.assertIsInstance(files, list)
        self.assertTrue(len(files) > 0)
        # Check that the inner item is a tuple, not a list
        # files = [("", (filename, file_obj))]
        self.assertIsInstance(files[0], tuple)
        self.assertEqual(len(files[0]), 2)
        self.assertIsInstance(files[0][1], tuple)

    @patch('discord_fs.client.time.sleep')
    @patch('discord_fs.client.httpx.request')
    def test_rate_limit(self, mock_request, mock_sleep):
        # Mock 429 response followed by 200 response
        mock_response_429 = MagicMock()
        mock_response_429.status_code = 429
        mock_response_429.headers = {"Retry-After": "1.5"}
        
        mock_response_200 = MagicMock()
        mock_response_200.status_code = 200
        
        mock_request.side_effect = [mock_response_429, mock_response_200]
        
        client = api.DiscordClient()
        response = client.get_message("123")
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(mock_request.call_count, 2)
        mock_sleep.assert_called_with(1.5)

    @patch('discord_fs.client.time.sleep')
    @patch('discord_fs.client.httpx.request')
    def test_rate_limit_max_retries(self, mock_request, mock_sleep):
        # Mock 429 response repeatedly
        mock_response_429 = MagicMock()
        mock_response_429.status_code = 429
        mock_response_429.headers = {"Retry-After": "0.1"}
        
        mock_request.return_value = mock_response_429
        
        client = api.DiscordClient()
        # Set max_retries via _make_request default or passed arg, 
        # but since we call get_message which calls _make_request with default, 
        # we rely on default max_retries=5.
        # However, get_message doesn't expose max_retries arg. 
        # So we test _make_request directly or rely on default.
        # Let's call _make_request directly for precise testing or assume default 5.
        
        response = client._make_request("GET", "http://test.com", max_retries=3)
        
        self.assertEqual(response.status_code, 429)
        # Initial call + 3 retries = 4 calls
        self.assertEqual(mock_request.call_count, 4) 
        self.assertEqual(mock_sleep.call_count, 3)

    @patch('discord_fs.client.httpx.request')
    def test_status_error(self, mock_request):
        # Mock 404 response
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError("404 Not Found", request=None, response=mock_response)
        
        mock_request.return_value = mock_response
        
        client = api.DiscordClient()
        
        with self.assertRaises(httpx.HTTPStatusError):
            client.get_message("123")

    @patch('discord_fs.commands.download.DiscordClient')
    @patch('discord_fs.commands.download.load_file_index')
    @patch('discord_fs.commands.download.get_file_index')
    @patch('builtins.open', new_callable=mock_open)
    @patch('os.makedirs')
    def test_download_retry_on_error(self, mock_makedirs, mock_file, mock_get_index, mock_load_index, MockClient):
        # Setup mocks
        mock_get_index.return_value = {
            "test_file": {
                "filename": utils.encode("test_file.txt"),
                "urls": [["msg_id", "att_id"]]
            }
        }
        
        mock_client_instance = MockClient.return_value
        
        # Mock get_message response
        mock_message_response = MagicMock()
        mock_message_response.status_code = 200
        mock_message_response.json.return_value = {
            "attachments": [{"url": "http://new-url.com"}]
        }
        mock_client_instance.get_message.return_value = mock_message_response
        
        # Mock download_file response
        # First call raises 404 (or any error), second call succeeds
        mock_error_response = MagicMock()
        mock_error_response.status_code = 404
        mock_error = httpx.HTTPStatusError("404 Not Found", request=None, response=mock_error_response)
        
        mock_200_response = MagicMock()
        mock_200_response.status_code = 200
        mock_200_response.content = b"file content"
        
        mock_client_instance.download_file.side_effect = [mock_error, mock_200_response]
        
        # Run download
        args = argparse.Namespace(id=["1"])
        commands.download_file(args)
        
        # Verify
        # Should call download_file twice
        self.assertEqual(mock_client_instance.download_file.call_count, 2)
        # Should call get_message twice (initial fetch + refresh)
        self.assertEqual(mock_client_instance.get_message.call_count, 2)
        # Should write to file
        mock_file().write.assert_called_with(b"file content")

    @patch('discord_fs.commands.download.DiscordClient')
    @patch('discord_fs.commands.download.load_file_index')
    @patch('discord_fs.commands.download.get_file_index')
    @patch('builtins.open', new_callable=mock_open)
    @patch('os.makedirs')
    def test_download_multi_chunk(self, mock_makedirs, mock_file, mock_get_index, mock_load_index, MockDiscordClient):
        # Setup mock client
        client_instance = MockDiscordClient.return_value
        
        # Mock get_message responses
        def get_message_side_effect(message_id):
            response = MagicMock()
            response.json.return_value = {
                'attachments': [{'url': f'http://example.com/{message_id}'}]
            }
            return response
        
        client_instance.get_message.side_effect = get_message_side_effect
        
        # Mock download_file responses
        def download_file_side_effect(url):
            response = MagicMock()
            response.content = f"content_of_{url}".encode('utf-8')
            return response
        
        client_instance.download_file.side_effect = download_file_side_effect

        # Setup mock index
        mock_get_index.return_value = {
            "test_file.txt": {
                "filename": utils.encode("test_file.txt"),
                "urls": [
                    ["msg1", "att1"],
                    ["msg2", "att2"]
                ]
            }
        }

        # Mock args
        args = argparse.Namespace(id=["1"])

        # Run download
        commands.download_file(args)

        # Verify calls
        # We expect client.get_message to be called for BOTH chunks
        client_instance.get_message.assert_any_call("msg1")
        client_instance.get_message.assert_any_call("msg2")
        
        # We expect client.download_file to be called for BOTH chunks
        client_instance.download_file.assert_any_call("http://example.com/msg1")
        client_instance.download_file.assert_any_call("http://example.com/msg2")

        # Verify file writes
        handle = mock_file()
        # We expect write to be called twice
        self.assertEqual(handle.write.call_count, 2)
        handle.write.assert_any_call(b"content_of_http://example.com/msg1")
        handle.write.assert_any_call(b"content_of_http://example.com/msg2")

if __name__ == '__main__':
    unittest.main()

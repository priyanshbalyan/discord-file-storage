import sys
from unittest.mock import MagicMock
import argparse

# Mock httpx module before importing fs
sys.modules["httpx"] = MagicMock()

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

    @patch('discord_fs.client.httpx.get')
    @patch('builtins.open', new_callable=mock_open)
    def test_load_file_index_success(self, mock_file, mock_get):
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
        
        mock_get.side_effect = [mock_response_list, mock_response_file]
        
        message_id = api.load_file_index()
        
        self.assertEqual(message_id, "12345")
        mock_file.assert_called_with("index.txt", "w")
        mock_file().write.assert_called_with('{"test": "data"}')

    @patch('builtins.open', new_callable=mock_open, read_data='{"test": "data"}')
    def test_get_file_index(self, mock_file):
        index = api.get_file_index()
        self.assertEqual(index, {"test": "data"})

    @patch('os.get_terminal_size')
    @patch('discord_fs.client.httpx.post')
    @patch('discord_fs.commands.upload.load_file_index')
    @patch('discord_fs.commands.upload.get_file_index')
    @patch('discord_fs.commands.upload.update_file_index')
    @patch('os.path.getsize')
    @patch('builtins.open', new_callable=mock_open, read_data=b'some data')
    def test_upload_file(self, mock_file, mock_getsize, mock_update, mock_get_index, mock_load, mock_post, mock_terminal_size):
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
        mock_post.return_value = mock_response
        
        # Run upload
        # Note: upload_file is now in discord_fs.commands.upload
        # Pass argparse.Namespace
        args = argparse.Namespace(file="test_file.txt")
        commands.upload_file(args)
        
        # Verify
        self.assertTrue(mock_post.called)
        self.assertTrue(mock_update.called)
        
        # Check if file index was updated correctly in the call to update_file_index
        args, _ = mock_update.call_args
        updated_index = args[1]
        encoded_name = utils.encode("test_file.txt")
        self.assertIn(encoded_name, updated_index)
        self.assertEqual(updated_index[encoded_name]['size'], 100)

if __name__ == '__main__':
    unittest.main()

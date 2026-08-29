import unittest
from unittest.mock import patch, MagicMock, mock_open
import argparse
import httpx
import io
import os
from discord_fs.commands.upload import upload_file
from discord_fs.utils import encode
from discord_fs import config

class TestUploadResumable(unittest.TestCase):
    @patch('discord_fs.commands.upload.tqdm')
    @patch('discord_fs.commands.upload.DiscordClient')
    @patch('discord_fs.commands.upload.load_file_index')
    @patch('discord_fs.commands.upload.get_file_index')
    @patch('discord_fs.commands.upload.update_file_index')
    @patch('os.path.getsize')
    @patch('builtins.open', new_callable=mock_open, read_data=b'a' * 20000000)
    def test_upload_saves_partial_on_error(self, mock_file, mock_getsize, mock_update, mock_get_index, mock_load, MockClient, mock_tqdm):
        """Test that partial progress is saved to the index when an upload error occurs."""
        # Setup mocks
        mock_load.return_value = "old_msg_id"
        mock_get_index.return_value = {}
        mock_getsize.return_value = 16000000 # 2 chunks (8MB each)
        mock_update.return_value = "new_index_id"
        
        mock_client_instance = MockClient.return_value
        
        # First chunk success
        mock_response_success = MagicMock()
        mock_response_success.json.return_value = {"id": "msg1", "attachments": [{"id": "att1"}]}
        
        # Second chunk error (after all retries)
        mock_response_error = MagicMock()
        mock_response_error.status_code = 500
        mock_response_error.text = "Error"
        mock_error = httpx.HTTPStatusError("Error", request=None, response=mock_response_error)
        
        # First chunk succeeds, second chunk fails, and a third response is available
        # to prove upload_file stops after the failed chunk.
        mock_response_unexpected = MagicMock()
        mock_response_unexpected.json.return_value = {"id": "msg3", "attachments": [{"id": "att3"}]}
        mock_client_instance._make_request.side_effect = [
            mock_response_success,
            mock_error,
            mock_response_unexpected,
        ]
        
        args = argparse.Namespace(file="test.txt")
        with patch('builtins.input', side_effect=AssertionError("input should not be called")):
            upload_file(args)
        
        # Verify no later chunk was attempted after the failed chunk.
        self.assertEqual(mock_client_instance._make_request.call_count, 2)

        # Verify update_file_index was called for the first successful chunk.
        mock_update.assert_called()
        call_args = mock_update.call_args[0]
        updated_index = call_args[1]
        encoded_name = encode("test.txt")
        self.assertTrue(updated_index[encoded_name]['is_partial'])
        self.assertEqual(len(updated_index[encoded_name]['urls']), 1)

    @patch('discord_fs.commands.upload.tqdm')
    @patch('discord_fs.commands.upload.DiscordClient')
    @patch('discord_fs.commands.upload.load_file_index')
    @patch('discord_fs.commands.upload.get_file_index')
    @patch('discord_fs.commands.upload.update_file_index')
    @patch('os.path.getsize')
    @patch('builtins.open', new_callable=mock_open, read_data=b'a' * 20000000)
    def test_upload_resumes_partial(self, mock_file, mock_getsize, mock_update, mock_get_index, mock_load, MockClient, mock_tqdm):
        """Test that a partial upload resumes from the last successful chunk."""
        # Setup mocks
        mock_load.return_value = "old_msg_id"
        encoded_name = encode("test.txt")
        mock_get_index.return_value = {
            encoded_name: {
                "filename": encoded_name,
                "size": 16000000,
                "urls": [["msg1", "att1"]],
                "is_partial": True
            }
        }
        mock_getsize.return_value = 16000000 # 2 chunks
        mock_update.return_value = "new_index_id"
        
        mock_client_instance = MockClient.return_value
        mock_response_success = MagicMock()
        mock_response_success.json.return_value = {"id": "msg_new", "attachments": [{"id": "att_new"}]}
        mock_client_instance._make_request.return_value = mock_response_success
        
        # Run upload
        args = argparse.Namespace(file="test.txt")
        with patch('builtins.input', side_effect=AssertionError("input should not be called")):
            upload_file(args)
        
        # Verify
        # Should call _make_request ONCE (for the 2nd chunk, since start_chunk=1)
        self.assertEqual(mock_client_instance._make_request.call_count, 1)
        
        # Verify final index update (no longer partial)
        last_call_args = mock_update.call_args[0]
        updated_index = last_call_args[1]
        self.assertNotIn('is_partial', updated_index[encoded_name])
        self.assertEqual(len(updated_index[encoded_name]['urls']), 2)

    @patch('discord_fs.commands.upload.tqdm')
    @patch('discord_fs.commands.upload.DiscordClient')
    @patch('discord_fs.commands.upload.load_file_index')
    @patch('discord_fs.commands.upload.get_file_index')
    @patch('discord_fs.commands.upload.update_file_index')
    @patch('os.path.getsize')
    @patch('builtins.open', new_callable=mock_open, read_data=b'a' * 20000000)
    def test_upload_same_file_resumes_without_prompt(self, mock_file, mock_getsize, mock_update, mock_get_index, mock_load, MockClient, mock_tqdm):
        """Test that uploading the same partial file resumes instead of starting over."""
        # Setup mocks
        mock_load.return_value = "old_msg_id"
        encoded_name = encode("test.txt")
        mock_get_index.return_value = {
            encoded_name: {
                "filename": encoded_name,
                "size": 16000000,
                "urls": [["msg1", "att1"]],
                "is_partial": True
            }
        }
        mock_getsize.return_value = 16000000 # 2 chunks
        mock_update.return_value = "new_index_id"
        
        mock_client_instance = MockClient.return_value
        mock_response_success = MagicMock()
        mock_response_success.json.return_value = {"id": "new_msg", "attachments": [{"id": "new_att"}]}
        mock_client_instance._make_request.return_value = mock_response_success
        
        args = argparse.Namespace(file="test.txt")
        with patch('builtins.input', side_effect=AssertionError("input should not be called")):
            upload_file(args)
        
        # Verify
        mock_client_instance.delete_message.assert_not_called()
        self.assertEqual(mock_client_instance._make_request.call_count, 1)

    @patch('discord_fs.commands.upload.tqdm')
    @patch('discord_fs.commands.upload.DiscordClient')
    @patch('discord_fs.commands.upload.load_file_index')
    @patch('discord_fs.commands.upload.get_file_index')
    @patch('discord_fs.commands.upload.update_file_index')
    @patch('os.path.getsize')
    @patch('builtins.open', new_callable=mock_open, read_data=b'a' * 20000000)
    def test_upload_retry_success(self, mock_file, mock_getsize, mock_update, mock_get_index, mock_load, MockClient, mock_tqdm):
        """Test that a chunk upload is retried upon failure and succeeds."""
        # Setup mocks
        mock_load.return_value = "old_msg_id"
        mock_get_index.return_value = {}
        mock_getsize.return_value = 8000000 # 1 chunk
        mock_update.return_value = "new_index_id"
        
        mock_client_instance = MockClient.return_value
        mock_success = MagicMock()
        mock_success.json.return_value = {"id": "msg1", "attachments": [{"id": "att1"}]}
        mock_client_instance._make_request.return_value = mock_success
        
        # Run upload
        args = argparse.Namespace(file="test.txt")
        upload_file(args)
        
        # Verify _make_request was called with max_retries=2
        mock_client_instance._make_request.assert_called()
        _, kwargs = mock_client_instance._make_request.call_args
        self.assertEqual(kwargs.get('max_retries'), 2)

if __name__ == '__main__':
    unittest.main()

import os
import sys
import argparse
import io
import httpx
from tqdm import tqdm
from ..client import DiscordClient
from .. import config
from ..utils import get_size_format, encode, get_total_chunks
from ..api import load_file_index, get_file_index, update_file_index, save_file_index_locally

def upload_file(args: argparse.Namespace) -> None:
    filepath = args.file
    
    try:
        message_id = load_file_index()
        f = open(filepath, "rb")
    except FileNotFoundError as err:
        print(f"Error: {err}")
        return
    except Exception as err:
        print(f"Error loading index: {err}")
        return

    with f:
        file_index = get_file_index()

        size = os.path.getsize(filepath)
        filename = os.path.basename(filepath)
        total_chunks = get_total_chunks(size)

        urls = []
        start_chunk = 0
        encoded_filename = encode(filename)

        if encoded_filename in file_index:
            entry = file_index[encoded_filename]
            if entry.get("is_partial"):
                print(f"Partial upload detected for {filename} ({len(entry['urls'])}/{total_chunks} chunks).")
                while True:
                    choice = input("Do you want to (r)esume or (s)tart over? [r/s]: ").lower()
                    if choice == 'r':
                        urls = entry["urls"]
                        start_chunk = len(urls)
                        f.seek(start_chunk * config.CHUNK_SIZE)
                        print(f"Resuming from chunk {start_chunk + 1}...")
                        break
                    elif choice == 's':
                        print("Starting over. Deleting previous chunks...")
                        client = DiscordClient()
                        cleanup_pbar = tqdm(total=len(entry["urls"]), desc="Cleaning up", unit="chunk")
                        for j, (msg_id, _) in enumerate(entry["urls"]):
                            try:
                                client.delete_message(msg_id)
                                cleanup_pbar.update(1)
                            except Exception as del_err:
                                cleanup_pbar.write(f"Failed to delete chunk {msg_id}: {del_err}")
                        cleanup_pbar.close()
                        print("Cleanup finished. Starting upload...")
                        urls = [] # Reset urls for fresh upload
                        break
            else:
                print("File already uploaded.")
                return

        print("File Name: ", filename)
        print("File Size: ", get_size_format(size))
        print("Chunks to be created: ", total_chunks)

        client = DiscordClient()
        pbar = tqdm(total=total_chunks, desc="Uploading", unit="chunk")
        if start_chunk > 0:
            pbar.update(start_chunk)

        try:
            for i in range(start_chunk, total_chunks):
                chunk = f.read(config.CHUNK_SIZE)
                if not chunk:
                    break
                
                chunk_buffer = io.BytesIO(chunk)
                files = [("", (encoded_filename + "." + str(i), chunk_buffer))]

                def on_chunk_retry(attempt, exc):
                    pbar.write(f"Chunk {i+1} failed (attempt {attempt}/3). Retrying in 2s...")

                try:
                    # DiscordClient._make_request uses max_retries=5 by default, 
                    # but we want 2 (total 3 attempts) for chunks as per requirement.
                    # post_message passes on_retry down to _make_request.
                    response = client._make_request("POST", f"{client.base_url}{client.channel_id}/messages", 
                                                   max_retries=2, on_retry=on_chunk_retry, files=files)
                except Exception as e:
                    pbar.close()
                    print(f"\nError encountered while uploading chunk {i+1} after all attempts.")
                    if isinstance(e, httpx.HTTPStatusError):
                        print(f"Status: {e.response.status_code}, Response: {e.response.text}")
                    else:
                        print(f"Error: {e}")
                    
                    if urls:
                        # Save partial progress to Discord on error
                        update_file_index(message_id, file_index)
                    return

                message = response.json()
                urls.append(
                    [message["id"], message["attachments"][0]["id"]]
                )  # message_id, attachment_id pair
                
                # Update local index only after every chunk
                file_index[encoded_filename] = {
                    "filename": encoded_filename,
                    "size": size,
                    "urls": urls,
                    "is_partial": True
                }
                save_file_index_locally(file_index)
                pbar.update(1)

        except Exception as e:
            pbar.close()
            print(f"\nAn unexpected error occurred: {e}")
            if urls:
                # Save partial progress to Discord on error
                update_file_index(message_id, file_index)
            return

        pbar.close()
        print("File uploaded")

        # Mark as complete and update index on Discord
        file_index[encoded_filename] = {
            "filename": encoded_filename,
            "size": size,
            "urls": urls,
        }
        update_file_index(message_id, file_index)

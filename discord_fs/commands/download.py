import os
import sys
import argparse
import httpx
from tqdm import tqdm
from ..client import DiscordClient
from .. import config
from ..utils import decode
from ..api import load_file_index, get_file_index

def download_file(args: argparse.Namespace) -> None:
    indices = []
    for arg in args.id:
        try:
            indices.append((int(arg[1:]) if arg.startswith("#") else int(arg)) - 1)
        except ValueError:
            print(f"Invalid ID format: {arg}")
            return

    try:
        load_file_index()
    except Exception as e:
        print(f"Error loading file index: {e}")
        return

    file_index = get_file_index()
    filelist = list(file_index.items())

    client = DiscordClient()
    for index in indices:
        if index >= len(filelist) or index < 0:
            print(f"Invalid ID provided: {index + 1}")
            continue

        og_name, file = filelist[index]
        filename = decode(file["filename"])
        print(f"Downloading {filename}...")
        
        target_path = os.path.abspath(f"downloads/{filename}")
        os.makedirs(os.path.dirname(target_path), exist_ok=True)
        
        try:
            with open(target_path, "wb") as f:
                    pbar = tqdm(total=len(file["urls"]), desc="Downloading", unit="chunk")
                    for i, values in enumerate(file["urls"]):
                        message_id, attachment_id = values

                        try:
                            # Use internal retry strategy for fetching metadata and content
                            response = client.get_message(message_id)
                            attachments = response.json()['attachments']
                            download_url = attachments[0]['url']
                            cdnResponse = client.download_file(download_url)
                        except Exception as e:
                            pbar.close()
                            print(f"An error occurred while downloading chunk {i+1}: {e}")
                            return

                        f.write(cdnResponse.content)
                        pbar.update(1)
                    pbar.close()
            
            print(f"Download complete. File saved to: {target_path}")
        except IOError as e:
            print(f"Error writing file {filename}: {e}")
            return
        except Exception as e:
            print(f"An unexpected error occurred during download: {e}")
            return

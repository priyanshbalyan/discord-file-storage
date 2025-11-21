import os
import sys
import argparse
import httpx
from ..client import DiscordClient
from .. import config
from ..utils import decode, show_progress_bar
from ..api import load_file_index, get_file_index

def download_file(args: argparse.Namespace) -> None:
    indices = []
    for arg in args.id:
        try:
            indices.append(int(arg[1:]) if arg.startswith("#") else int(arg) - 1)
        except ValueError:
            print(f"Invalid ID format: {arg}")
            return

    load_file_index()
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
        
        os.makedirs(os.path.dirname(f"downloads/{filename}"), exist_ok=True)
        
        try:
            with open("downloads/" + filename, "wb") as f:
                    for i, values in enumerate(file["urls"]):
                        message_id, attachment_id = values

                        try:
                            response = client.get_message(message_id)
                        except httpx.HTTPStatusError as e:
                            print(f"An error occurred while loading messages: {e.response.status_code} {e.response.text}")
                            return # Stop downloading this file

                    attachments = response.json()['attachments']
                    download_url = attachments[0]['url']

                    try:
                        cdnResponse = client.download_file(download_url)  # download from url with identification params
                    except httpx.HTTPStatusError as e:
                        print(f"An error occurred while downloading the file: {e.response.status_code} {e.response.text}")
                        return # Stop downloading this file

                    show_progress_bar(i + 1, len(file["urls"]))
                    f.write(cdnResponse.content)
        except IOError as e:
            print(f"Error writing file {filename}: {e}")
            return

    print("Download complete.")

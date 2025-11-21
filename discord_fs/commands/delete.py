import sys
import argparse
import httpx
from ..client import DiscordClient

from .. import config
from ..utils import decode, show_progress_bar
from ..api import load_file_index, get_file_index, update_file_index

def delete_file(args: argparse.Namespace) -> None:
    
    index_message_id = load_file_index()
    if not index_message_id:
        print("Could not load file index.")
        return

    file_index = get_file_index()
    file_list = list(file_index.values())
    
    for raw_id in args.id:
        try:
            index = (int(raw_id[1:]) if raw_id.startswith("#") else int(raw_id)) - 1
        except ValueError:
            print(f"Invalid ID format: {raw_id}")
            continue

        if index >= len(file_list) or index < 0:
            print(f"Invalid ID provided: {raw_id}")
            continue

        file = file_list[index]
        message_ids = [i[0] for i in file["urls"]]
        print(f"Deleting {decode(file['filename'])}...")

        for i in range(len(message_ids)):
            client = DiscordClient()
            try:
                client.delete_message(message_ids[i])
            except httpx.HTTPStatusError as e:
                print(
                    "An error occurred while deleting file:",
                    e.response.status_code,
                    e.response.text,
                )
                break

            show_progress_bar(i + 1, len(message_ids))

        else:
            # Only execute if loop finished without break
            if file["filename"] in file_index:
                del file_index[file["filename"]]
                print(f"Deleted {decode(file['filename'])}.")

    update_file_index(index_message_id, file_index)


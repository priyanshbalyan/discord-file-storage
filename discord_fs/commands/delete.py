import sys
import argparse
import httpx
from tqdm import tqdm
from ..client import DiscordClient

from .. import config
from ..utils import decode
from ..api import load_file_index, get_file_index, update_file_index

def delete_file(args: argparse.Namespace) -> None:
    
    try:
        index_message_id = load_file_index()
        if not index_message_id:
            print("No index file found on server.")
            return
    except Exception as e:
        print(f"Error loading file index: {e}")
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

        pbar = tqdm(total=len(message_ids), desc="Deleting", unit="chunk")
        try:
            for i in range(len(message_ids)):
                client = DiscordClient()
                try:
                    client.delete_message(message_ids[i])
                except httpx.HTTPStatusError as e:
                    pbar.close()
                    print(
                        f"An error occurred while deleting file: {e.response.status_code} {e.response.text}"
                    )
                    break

                pbar.update(1)
            else:
                pbar.close()
        except Exception as e:
            pbar.close()
            print(f"An unexpected error occurred during deletion: {e}")
            break

        # Only delete from index if loop finished without break or if some chunks were deleted 
        if file["filename"] in file_index:
            del file_index[file["filename"]]
            print(f"Deleted {decode(file['filename'])}.")

    try:
        update_file_index(index_message_id, file_index)
    except Exception as e:
        print(f"Error updating file index after deletion: {e}")

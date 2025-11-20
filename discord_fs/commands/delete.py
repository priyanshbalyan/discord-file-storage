import sys
import requests
from time import sleep
from .. import config
from ..utils import decode, show_progress_bar
from ..api import load_file_index, get_file_index, update_file_index

def delete_file(args):
    index = (int(args[0][1:]) if args[0][0] == "#" else int(args[0])) - 1
    index_message_id = load_file_index()

    file_index = get_file_index()
    file_list = list(file_index.values())
    if index >= len(file_list):
        print("Invalid ID provided")
        sys.exit()

    file = file_list[index]
    message_ids = [i[0] for i in file["urls"]]
    print("Deleting...")

    for i in range(len(message_ids)):
        response = requests.delete(
            f"{config.BASE_URL}{config.CHANNEL_ID}/messages/{message_ids[i]}", headers=config.HEADERS
        )
        if response.status_code != 204:
            print(
                "An error occurred while deleting file:",
                response.status_code,
                response.text,
            )
            sys.exit()

        show_progress_bar(i + 1, len(message_ids))
        sleep(1)

    del file_index[file["filename"]]
    update_file_index(index_message_id, file_index)
    print(f"Deleted {decode(file['filename'])}.")

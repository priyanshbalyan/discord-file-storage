import os
import sys
import io
import requests
from .. import config
from ..utils import get_size_format, encode, get_total_chunks, show_progress_bar
from ..api import load_file_index, get_file_index, update_file_index

def upload_file(args):
    message_id = load_file_index()
    try:
        f = open(args[0], "rb")
    except FileNotFoundError as err:
        print(err)
        sys.exit()

    with f:
        file_index = get_file_index()

        size = os.path.getsize(args[0])
        filename = os.path.basename(args[0])
        total_chunks = get_total_chunks(size)

        if encode(filename) in file_index:
            print("File already uploaded.")
            sys.exit()

        print("File Name: ", filename)
        print("File Size: ", get_size_format(size))
        print("Chunks to be created: ", total_chunks)
        print("Uploading...")

        urls = []
        for i in range(total_chunks):
            show_progress_bar(i + 1, total_chunks)
            chunk = io.BytesIO(f.read(config.CHUNK_SIZE))  # Read file in 8MB chunks
            files = [["", [encode(filename) + "." + str(i), chunk]]]

            response = requests.post(
                f"{config.BASE_URL}{config.CHANNEL_ID}/messages", headers=config.HEADERS, files=files
            )
            if response.status_code != 200:
                print("Error encountered while uploading file:", response.text)
                sys.exit()

            message = response.json()
            urls.append(
                [message["id"], message["attachments"][0]["id"]]
            )  # message_id, attachment_id pair

        print("File uploaded")

        file_index[encode(filename)] = {
            "filename": encode(filename),
            "size": size,
            "urls": urls,
        }
        update_file_index(message_id, file_index)

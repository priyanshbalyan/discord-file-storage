import os
import sys
import io
from ..client import DiscordClient
from .. import config
from ..utils import get_size_format, encode, get_total_chunks, show_progress_bar
from ..api import load_file_index, get_file_index, update_file_index

def upload_file(args):
    filepath = args.file
    
    message_id = load_file_index()
    try:
        f = open(filepath, "rb")
    except FileNotFoundError as err:
        print(err)
        return

    with f:
        file_index = get_file_index()

        size = os.path.getsize(filepath)
        filename = os.path.basename(filepath)
        total_chunks = get_total_chunks(size)

        if encode(filename) in file_index:
            print("File already uploaded.")
            return

        print("File Name: ", filename)
        print("File Size: ", get_size_format(size))
        print("Chunks to be created: ", total_chunks)
        print("Uploading...")

        urls = []
        for i in range(total_chunks):
            show_progress_bar(i + 1, total_chunks)
            chunk = io.BytesIO(f.read(config.CHUNK_SIZE))  # Read file in 8MB chunks
            files = [["", [encode(filename) + "." + str(i), chunk]]]

            client = DiscordClient()
            response = client.post_message(files=files)
            if response.status_code != 200:
                print("Error encountered while uploading file:", response.text)
                return

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

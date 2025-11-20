import os
import sys
import requests
from .. import config
from ..utils import decode, show_progress_bar
from ..api import load_file_index, get_file_index

def download_file(args):
    indices = []
    for arg in args:
        indices.append(int(arg[1:]) if arg[0] == "#" else int(arg) - 1)

    load_file_index()
    file_index = get_file_index()
    filelist = list(file_index.items())

    for index in indices:
        if index >= len(filelist):
            print(f"Invalid ID provided: {index}")
            sys.exit()

        print("Downloading...")

        og_name, file = filelist[index]
        filename = decode(file["filename"])
        os.makedirs(os.path.dirname(f"downloads/{filename}"), exist_ok=True)
        
        with open("downloads/" + filename, "wb") as f:
            for i, values in enumerate(file["urls"]):
                message_id, attachment_id = values

                response = requests.get(f"{config.BASE_URL}{config.CHANNEL_ID}/messages/{message_id}", headers=config.HEADERS)
                if response.status_code != 200:
                    print("An error occurred while loading messages: ", response.status_code, response.text)
                    sys.exit()

                attachments = response.json()['attachments']
                download_url = attachments[0]['url']

                cdnResponse = requests.get(download_url)  # download from url with identification params
                if cdnResponse.status_code != 200:
                    print("An error occurred while downloading the file:", cdnResponse.status_code, cdnResponse.text)
                    sys.exit()

                show_progress_bar(i + 1, len(file["urls"]))
                f.write(cdnResponse.content)

    print("Download complete.")

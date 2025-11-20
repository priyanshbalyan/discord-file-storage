import requests
import json
import sys
from . import config

def load_file_index():
    # Ensure configuration is loaded
    
    response = requests.get(f"{config.BASE_URL}{config.CHANNEL_ID}/messages?limit=1", headers=config.HEADERS)
    if response.status_code != 200:
        print(
            "An error occurred while loading index: ",
            response.status_code,
            response.text,
        )
        sys.exit()
    if len(response.json()) < 1:
        print("No index file found")
        return

    last_message = response.json()[0]
    file = last_message["attachments"][0]
    filename = file["filename"]
    url = file["url"]

    if filename != config.INDEX_FILE:
        print("No index file found")
        return

    with open(config.INDEX_FILE, "w") as f:
        response = requests.get(url)
        f.write(response.text)

    return last_message["id"]


def get_file_index():
    try:
        with open(config.INDEX_FILE, "r") as f:
            data = f.read()
        return json.loads(data)
    except FileNotFoundError:
        return dict()


def update_file_index(index_id, file_index):
    # Ensure we have latest headers
    
    with open(config.INDEX_FILE, "w") as f:
        f.write(json.dumps(file_index))

    files = [["", [config.INDEX_FILE, open(config.INDEX_FILE, "rb")]]]

    # deleting existing index file on the channel
    if index_id:
        print("Deleting old index file")
        response = requests.delete(
            f"{config.BASE_URL}{config.CHANNEL_ID}/messages/{index_id}", headers=config.HEADERS
        )
        if response.status_code != 204:
            print(
                "An error occurred while deleting old index file:",
                response.status_code,
                response.text,
            )

    # Uploading new update index file
    print("Uploading new updated index file")
    response = requests.post(
        f"{config.BASE_URL}{config.CHANNEL_ID}/messages", headers=config.HEADERS, files=files
    )
    if response.status_code != 200:
        print("An error occurred while updating index:", response.text)
    print("Done.")

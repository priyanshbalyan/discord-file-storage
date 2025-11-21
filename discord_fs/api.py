from .client import DiscordClient
from typing import Any
import json
from . import config

class APIError(Exception):
    pass

def load_file_index() -> str | None:
    # Ensure configuration is loaded
    
    client = DiscordClient()
    response = client.get_messages(limit=1)
    if response.status_code != 200:
        raise APIError(f"An error occurred while loading index: {response.status_code} {response.text}")

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
        # client is already initialized above
        response = client.download_file(url)
        f.write(response.text)

    return last_message["id"]


def get_file_index() -> dict[str, Any]:
    try:
        with open(config.INDEX_FILE, "r") as f:
            data = f.read()
        return json.loads(data)
    except FileNotFoundError:
        return dict()


def update_file_index(index_id: str | None, file_index: dict[str, Any]) -> None:
    # Ensure we have latest headers
    
    with open(config.INDEX_FILE, "w") as f:
        f.write(json.dumps(file_index))

    files = [["", [config.INDEX_FILE, open(config.INDEX_FILE, "rb")]]]

    # deleting existing index file on the channel
    if index_id:
        print("Deleting old index file")
        client = DiscordClient()
        response = client.delete_message(index_id)
        if response.status_code != 204:
            print(
                "An error occurred while deleting old index file:",
                response.status_code,
                response.text,
            )

    # Uploading new update index file
    print("Uploading new updated index file")
    # client might not be initialized if index_id was None, so ensure it is
    client = DiscordClient()
    response = client.post_message(files=files)
    if response.status_code != 200:
        raise APIError(f"An error occurred while updating index: {response.text}")
    print("Done.")

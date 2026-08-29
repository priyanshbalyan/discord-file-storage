from .client import DiscordClient
import httpx
from typing import Any
import json
from . import config

class APIError(Exception):
    pass

def load_file_index() -> str | None:
    # Ensure configuration is loaded
    
    client = DiscordClient()
    try:
        response = client.get_messages(limit=100)
    except httpx.HTTPStatusError as e:
        raise APIError(f"An error occurred while loading index: {e.response.status_code} {e.response.text}")

    messages = response.json()
    if len(messages) < 1:
        print("No index file found")
        return

    for message in messages:
        for file in message.get("attachments", []):
            filename = file.get("filename")
            url = file.get("url")

            if filename != config.INDEX_FILE or not url:
                continue

            with open(config.INDEX_FILE, "w") as f:
                # client is already initialized above
                response = client.download_file(url)
                f.write(response.text)

            return message["id"]

    print("No index file found")
    return


def get_file_index() -> dict[str, Any]:
    try:
        with open(config.INDEX_FILE, "r") as f:
            data = f.read()
        return json.loads(data)
    except FileNotFoundError:
        return dict()


def save_file_index_locally(file_index: dict[str, Any]) -> None:
    with open(config.INDEX_FILE, "w") as f:
        f.write(json.dumps(file_index))


def update_file_index(index_id: str | None, file_index: dict[str, Any]) -> str:
    # Ensure we have latest headers
    
    with open(config.INDEX_FILE, "w") as f:
        f.write(json.dumps(file_index))

    # deleting existing index file on the channel
    if index_id:
        print("\nDeleting old index file")
        client = DiscordClient()
        try:
            client.delete_message(index_id)
        except httpx.HTTPStatusError as e:
            print(
                "An error occurred while deleting old index file:",
                e.response.status_code,
                e.response.text,
            )

    # Uploading new update index file
    print("\nUploading new updated index file")
    # client might not be initialized if index_id was None, so ensure it is
    client = DiscordClient()
    try:
        with open(config.INDEX_FILE, "rb") as f:
            files = [("", (config.INDEX_FILE, f))]
            response = client.post_message(files=files)
    except httpx.HTTPStatusError as e:
        raise APIError(f"An error occurred while updating index: {e.response.text}")
    print("Done.")
    return response.json()["id"]

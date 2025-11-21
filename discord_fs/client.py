import httpx
from . import config

class DiscordClient:
    def __init__(self):
        self.base_url = config.BASE_URL
        self.channel_id = config.CHANNEL_ID
        self.headers = config.HEADERS

    def get_messages(self, limit: int = 1) -> httpx.Response:
        url = f"{self.base_url}{self.channel_id}/messages"
        params = {"limit": limit}
        return httpx.get(url, headers=self.headers, params=params)

    def get_message(self, message_id: str) -> httpx.Response:
        url = f"{self.base_url}{self.channel_id}/messages/{message_id}"
        return httpx.get(url, headers=self.headers)

    def post_message(self, files: list) -> httpx.Response:
        url = f"{self.base_url}{self.channel_id}/messages"
        return httpx.post(url, headers=self.headers, files=files)

    def delete_message(self, message_id: str) -> httpx.Response:
        url = f"{self.base_url}{self.channel_id}/messages/{message_id}"
        return httpx.delete(url, headers=self.headers)

    def download_file(self, url: str) -> httpx.Response:
        return httpx.get(url)

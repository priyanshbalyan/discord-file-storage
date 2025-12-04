import httpx
import time
from . import config

class DiscordClient:
    def __init__(self):
        self.base_url = config.BASE_URL
        self.channel_id = config.CHANNEL_ID
        self.headers = config.HEADERS

    def _make_request(self, method: str, url: str, max_retries: int = 5, **kwargs) -> httpx.Response:
        while True:
            response = httpx.request(method, url, headers=self.headers, **kwargs)
            if response.status_code == 429:
                if max_retries <= 0:
                    print("Max retries reached. Returning response.")
                    return response
                
                retry_after = float(response.headers.get("Retry-After", 1))
                print(f"\nRate limited. Retrying after {retry_after} seconds...")
                time.sleep(retry_after)
                max_retries -= 1
                continue
            
            response.raise_for_status()
            return response

    def get_messages(self, limit: int = 1) -> httpx.Response:
        url = f"{self.base_url}{self.channel_id}/messages"
        params = {"limit": limit}
        return self._make_request("GET", url, params=params)

    def get_message(self, message_id: str) -> httpx.Response:
        url = f"{self.base_url}{self.channel_id}/messages/{message_id}"
        return self._make_request("GET", url)

    def post_message(self, files: list) -> httpx.Response:
        url = f"{self.base_url}{self.channel_id}/messages"
        return self._make_request("POST", url, files=files)

    def delete_message(self, message_id: str) -> httpx.Response:
        url = f"{self.base_url}{self.channel_id}/messages/{message_id}"
        return self._make_request("DELETE", url)

    def download_file(self, url: str) -> httpx.Response:
        return self._make_request("GET", url)

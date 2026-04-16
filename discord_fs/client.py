import httpx
import time
from typing import Callable
from . import config
from .utils import with_retry

class DiscordClient:
    def __init__(self):
        self.base_url = config.BASE_URL
        self.channel_id = config.CHANNEL_ID
        self.headers = config.HEADERS

    def _make_request(self, method: str, url: str, max_retries: int = 5, on_retry: Callable[[int, Exception], None] | None = None, **kwargs) -> httpx.Response:
        def internal_on_retry(attempt, exc):
            # Reset file buffers if present
            if "files" in kwargs:
                for item in kwargs["files"]:
                    try:
                        if hasattr(item[1][1], "seek"):
                            item[1][1].seek(0)
                    except (IndexError, TypeError):
                        continue
            
            # Call external callback if provided
            if on_retry:
                on_retry(attempt, exc)

        def make_call():
            response = httpx.request(method, url, headers=self.headers, **kwargs)
            if response.status_code == 429:
                retry_after = float(response.headers.get("Retry-After", 1))
                print(f"\nRate limited. Retrying after {retry_after} seconds...")
                time.sleep(retry_after)
                raise httpx.HTTPStatusError("Rate limited", request=response.request, response=response)
            
            response.raise_for_status()
            return response

        return with_retry(
            make_call, 
            max_retries=max_retries, 
            exceptions=(httpx.HTTPStatusError, httpx.RequestError),
            on_retry=internal_on_retry
        )

    def get_messages(self, limit: int = 1) -> httpx.Response:
        url = f"{self.base_url}{self.channel_id}/messages"
        params = {"limit": limit}
        return self._make_request("GET", url, params=params)

    def get_message(self, message_id: str) -> httpx.Response:
        url = f"{self.base_url}{self.channel_id}/messages/{message_id}"
        return self._make_request("GET", url)

    def post_message(self, files: list, on_retry: Callable[[int, Exception], None] | None = None) -> httpx.Response:
        url = f"{self.base_url}{self.channel_id}/messages"
        return self._make_request("POST", url, files=files, on_retry=on_retry)

    def delete_message(self, message_id: str) -> httpx.Response:
        url = f"{self.base_url}{self.channel_id}/messages/{message_id}"
        return self._make_request("DELETE", url)

    def download_file(self, url: str) -> httpx.Response:
        return self._make_request("GET", url)


import requests
from bs4 import BeautifulSoup
import time
import random
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type


class _RetryableError(Exception):
    """Raised for HTTP errors that warrant a retry (429, 5xx)."""


class BaseScraper:
    """
    Base class for web scrapers with:
    - Browser-like request headers to reduce blocking
    - Configurable random delay between requests
    - Automatic retry with exponential backoff for transient errors (429, 5xx)
    - Non-retryable handling for 403 Forbidden
    """

    def __init__(self, base_url, headers=None, delay_range=(1, 3)):
        self.base_url = base_url
        self.delay_range = delay_range
        self.headers = headers or {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'max-age=0',
        }

    def get_page(self, url, params=None):
        """
        Fetch a URL and return a BeautifulSoup object.

        - Adds a random delay before each request.
        - Retries up to 3 times with exponential backoff on 429 or 5xx errors.
        - Returns None on 403 (non-retryable) or after exhausting retries.
        """
        delay = random.uniform(*self.delay_range)
        print(f"  [fetch] Waiting {delay:.1f}s then fetching: {url}")
        time.sleep(delay)
        return self._fetch_with_retry(url, params)

    @retry(
        retry=retry_if_exception_type(_RetryableError),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=30),
        reraise=False,
    )
    def _fetch_with_retry(self, url, params):
        """Internal fetch — decorated with retry logic for transient errors."""
        try:
            response = requests.get(url, headers=self.headers, params=params, timeout=15)

            if response.status_code == 403:
                print(f"  [fetch] 403 Forbidden — not retrying: {url}")
                return None

            if response.status_code == 429:
                print(f"  [fetch] 429 Too Many Requests — will retry after backoff.")
                raise _RetryableError("Rate limited (429)")

            if response.status_code >= 500:
                print(f"  [fetch] {response.status_code} Server Error — will retry.")
                raise _RetryableError(f"Server error ({response.status_code})")

            response.raise_for_status()
            return BeautifulSoup(response.content, 'html.parser')

        except _RetryableError:
            raise  # Let tenacity handle it
        except requests.exceptions.ConnectionError as e:
            print(f"  [fetch] Connection error — will retry: {e}")
            raise _RetryableError(f"Connection error: {e}")
        except requests.exceptions.Timeout:
            print(f"  [fetch] Request timed out — will retry.")
            raise _RetryableError("Timeout")
        except requests.exceptions.RequestException as e:
            print(f"  [fetch] Non-retryable request error: {e}")
            return None

    def scrape(self, *args, **kwargs):
        """To be implemented by subclasses."""
        raise NotImplementedError("Subclasses must implement the scrape method.")

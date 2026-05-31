
import sys
import os
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from florist_scraper import FloristScraper


class ParallelScraper:
    """
    Scrapes multiple city/state combinations concurrently using ThreadPoolExecutor.

    Uses a shared rate limiter (threading.Lock + sleep) to avoid overwhelming
    the target site across all worker threads.

    Example:
        scraper = ParallelScraper(max_workers=3, delay_between_requests=2.0)
        df = scraper.scrape([("Austin", "TX"), ("Dallas", "TX"), ("Houston", "TX")])
    """

    def __init__(self, max_workers=3, delay_between_requests=2.0, num_pages=1):
        self.max_workers = max_workers
        self.delay = delay_between_requests
        self.num_pages = num_pages
        self._lock = threading.Lock()
        self._last_request_time = 0.0

    def _rate_limited_scrape(self, city, state):
        """Scrape one city/state pair with shared rate limiting."""
        with self._lock:
            elapsed = time.time() - self._last_request_time
            if elapsed < self.delay:
                time.sleep(self.delay - elapsed)
            self._last_request_time = time.time()

        print(f"[parallel] Scraping {city}, {state}...")
        scraper = FloristScraper(city, state)
        df = scraper.scrape(num_pages=self.num_pages)
        print(f"[parallel] {city}, {state} — {len(df)} records scraped.")
        return df

    def scrape(self, city_state_list):
        """
        Scrape multiple city/state pairs concurrently.

        Args:
            city_state_list: list of (city, state) tuples,
                             e.g. [("Austin", "TX"), ("Dallas", "TX")]

        Returns:
            pd.DataFrame: Combined results from all cities.
        """
        results = []
        errors = []

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {
                executor.submit(self._rate_limited_scrape, city, state): (city, state)
                for city, state in city_state_list
            }

            for future in as_completed(futures):
                city, state = futures[future]
                try:
                    df = future.result()
                    if df is not None and not df.empty:
                        results.append(df)
                except Exception as e:
                    print(f"[parallel] Error scraping {city}, {state}: {e}")
                    errors.append((city, state, str(e)))

        if not results:
            print("[parallel] No data scraped from any city.")
            return pd.DataFrame()

        combined = pd.concat(results, ignore_index=True)
        print(f"[parallel] Total records from {len(results)} cities: {len(combined)}")
        return combined


if __name__ == '__main__':
    cities = [("Austin", "TX"), ("Dallas", "TX")]
    scraper = ParallelScraper(max_workers=2, num_pages=1)
    df = scraper.scrape(cities)
    print(f"\nTotal scraped: {len(df)}")
    if not df.empty:
        print(df[['name', 'phone', 'city', 'state']].head(10))

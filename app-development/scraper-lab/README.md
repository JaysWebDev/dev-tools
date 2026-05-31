# Scraper Lab

Modular web scraping framework built in progressive layers — each module standalone and composable.

## Structure

| Path | Description |
|------|-------------|
| `foundations/` | Data cleaning utilities: addresses, phone, email, URLs, business names, geocoding |
| `cleaners/` | Pipeline-stage cleaning: engine, deduplication, quality scoring, schema validation |
| `base_scraper.py` | Base class for all scrapers — request handling, retry logic, rate limiting |
| `parallel_scraper.py` | Thread-pool scraper for bulk target lists |

## Usage

```python
from base_scraper import BaseScraper
from foundations.clean_addresses import clean_address
from cleaners.deduplicator import deduplicate

class MyScraper(BaseScraper):
    def parse(self, soup):
        # extract and return data dict
        ...
```

## Requirements

```bash
pip install requests beautifulsoup4 geopy
```

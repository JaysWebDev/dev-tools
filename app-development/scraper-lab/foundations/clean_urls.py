
import re
from urllib.parse import urlparse, urlunparse, parse_qs, urlencode

def clean_url(url_string):
    """
    Cleans a URL by adding https:// if missing, removing tracking parameters, and normalizing.

    Args:
        url_string (str): The raw URL string.

    Returns:
        str: The cleaned and standardized URL, or None if invalid.
    """
    print(f"\n--- Cleaning URL: {url_string} ---")

    if not isinstance(url_string, str) or not url_string.strip():
        print("Step 1: Invalid input (not a string or empty).")
        return None

    # Step 1: Add https:// if protocol is missing
    if not re.match(r"^[a-zA-Z]+://", url_string):
        cleaned_url = "https://" + url_string
        print(f"Step 1: Added https:// -> {cleaned_url}")
    else:
        cleaned_url = url_string
        print(f"Step 1: Protocol already present: {cleaned_url}")

    try:
        parsed_url = urlparse(cleaned_url)
        print(f"Step 2: Parsed URL: {parsed_url}")

        # Step 2: Remove common tracking parameters
        query_params = parse_qs(parsed_url.query)
        tracking_params = [
            "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
            "gclid", "fbclid", "_ga", "_gl", "_hsenc", "_hsmi", "mc_cid", "mc_eid"
        ]
        filtered_query_params = {k: v for k, v in query_params.items() if k not in tracking_params}
        print(f"Step 3: Filtered query parameters: {filtered_query_params}")

        # Reconstruct the query string
        new_query = urlencode(filtered_query_params, doseq=True)

        # Reconstruct the URL without fragment and with cleaned query
        final_url = urlunparse(
            (parsed_url.scheme, parsed_url.netloc, parsed_url.path, parsed_url.params, new_query, "")
        )
        print(f"Step 4: Reconstructed URL: {final_url}")

        return final_url
    except Exception as e:
        print(f"Step 2: Error parsing or cleaning URL: {e}")
        return None

if __name__ == '__main__':
    test_urls = [
        "www.example.com/page?utm_source=google&param1=value1#section",
        "example.com/path/to/resource",
        "http://anothersite.org/index.html?gclid=123xyz",
        "https://sub.domain.net",
        "ftp://files.server.com/data.zip", # Should remain ftp
        "invalid-url",
        "",
        None
    ]

    for url in test_urls:
        if url is None:
            print(f"\n--- Cleaning URL: None ---")
            print("Step 1: Input is None.")
            cleaned = clean_url(url)
        else:
            cleaned = clean_url(url)
        print(f"Result: {cleaned}")

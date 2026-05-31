
import time
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError

_geocoder = None
_cache = {}

def _get_geocoder():
    global _geocoder
    if _geocoder is None:
        _geocoder = Nominatim(user_agent="personal_scraper_lab/1.0")
    return _geocoder


def geocode_address(address_str):
    """
    Geocode a full address string to latitude/longitude using OpenStreetMap Nominatim.

    Free to use, no API key required.
    Rate limit: max 1 request/second per Nominatim ToS — enforced internally.

    Args:
        address_str (str): Full address, e.g. "123 Main St, Austin, TX 78701"

    Returns:
        dict: {"lat": float, "lon": float} or None if geocoding fails.
    """
    if not isinstance(address_str, str) or not address_str.strip():
        return None

    key = address_str.strip().lower()
    if key in _cache:
        return _cache[key]

    geocoder = _get_geocoder()
    time.sleep(1.1)  # Nominatim ToS: max 1 req/sec

    try:
        location = geocoder.geocode(address_str, timeout=10)
        if location:
            result = {'lat': round(location.latitude, 6), 'lon': round(location.longitude, 6)}
            _cache[key] = result
            print(f"  [geocode] {address_str} → {result}")
            return result
        else:
            print(f"  [geocode] No result for: {address_str}")
            _cache[key] = None
            return None
    except (GeocoderTimedOut, GeocoderServiceError) as e:
        print(f"  [geocode] Error geocoding '{address_str}': {e}")
        return None


def geocode_dataframe(df, address_col='address'):
    """
    Add lat/lon columns to a DataFrame by geocoding the address column.

    Args:
        df (pd.DataFrame): DataFrame with an address column.
        address_col (str): Column name containing full address strings.

    Returns:
        pd.DataFrame: Original DataFrame with lat and lon columns added.
    """
    import pandas as pd
    df = df.copy()
    results = df[address_col].apply(geocode_address)
    df['lat'] = results.apply(lambda r: r['lat'] if r else None)
    df['lon'] = results.apply(lambda r: r['lon'] if r else None)
    return df


if __name__ == '__main__':
    test_addresses = [
        "123 Main St, Austin, TX 78701",
        "1616 Lavaca St, Austin, TX 78701",
    ]
    for addr in test_addresses:
        result = geocode_address(addr)
        print(f"Result: {result}")

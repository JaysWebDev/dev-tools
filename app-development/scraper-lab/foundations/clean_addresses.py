
import re

def clean_address(address_str):
    """
    Parses and standardizes an address string into its components.
    Returns a dict with keys: street, unit, city, state, zip — or None if parsing fails.

    Handles:
    - Unit/Suite/Apt/Ste/# secondary address components
    - Multi-word street names and directionals (N, S, E, W, NE, etc.)
    - Highway and Route addresses
    - Standard "123 Main St, Austin, TX 78701" format
    """
    print(f"\n--- Cleaning Address: {address_str} ---")

    if not isinstance(address_str, str) or not address_str.strip():
        print("Step 1: Invalid input (not a string or empty).")
        return None

    address_str = address_str.strip()
    print(f"Step 1: Input address: '{address_str}'")

    # --- Strategy: parse on the ORIGINAL comma-separated string, not stripped ---
    # Pattern breakdown:
    #   street: everything up to the first comma (handles multi-word names, directionals)
    #   unit (optional): Ste/Suite/Unit/Apt/# followed by identifier, before the city comma
    #   city: text between last unit/street comma and state
    #   state: 2-letter abbreviation
    #   zip: 5 digits, optionally followed by -4 digits

    # First, try to detect and extract a secondary unit from the street portion
    # e.g., "2124 E 6th St Unit 103, Austin, TX 78702"
    #   or  "632 Ralph Ablanedo Dr Ste 200, Austin, TX 78748"
    UNIT_PATTERN = r'(?i)\b(ste|suite|unit|apt|apartment|#|bldg|building|floor|fl)\s*[\w-]+'

    # Full address regex — works on original comma-separated format
    FULL_REGEX = re.compile(
        r'^(?P<street>.+?)'                                   # street (lazy)
        r'(?:,\s*(?P<unit>(?:ste|suite|unit|apt|apartment|#|bldg|building)\s*[\w-]+))?'  # optional unit
        r',\s*(?P<city>[^,]+?)'                               # city
        r',\s*(?P<state>[A-Za-z]{2})'                         # state
        r'\s+(?P<zip>\d{5}(?:-\d{4})?)$',                    # zip
        re.IGNORECASE
    )

    match = FULL_REGEX.match(address_str)

    if match:
        street = match.group('street').strip()
        unit = match.group('unit')
        city = match.group('city').strip()
        state = match.group('state').upper()
        zip_code = match.group('zip')

        # Check if unit is embedded in the street string (e.g., "123 Main St Unit 5")
        embedded = re.search(UNIT_PATTERN, street, re.IGNORECASE)
        if embedded and not unit:
            unit = embedded.group(0).strip()
            street = street[:embedded.start()].strip()

        parsed = {
            'street': street,
            'unit': unit.strip() if unit else None,
            'city': city,
            'state': state,
            'zip': zip_code
        }
        print(f"Step 2: Successfully parsed: {parsed}")
        return parsed

    # --- Fallback: handle addresses missing commas ---
    print("Step 2: Standard regex failed. Attempting fallback parser.")

    # Try splitting on state+zip at the end: "... Austin TX 78701"
    fallback = re.search(
        r'^(?P<street>.+?)\s+(?P<city>[A-Za-z][A-Za-z\s]+?)\s+(?P<state>[A-Z]{2})\s+(?P<zip>\d{5}(?:-\d{4})?)$',
        address_str.strip()
    )
    if fallback:
        street = fallback.group('street').strip()
        unit_match = re.search(UNIT_PATTERN, street, re.IGNORECASE)
        unit = None
        if unit_match:
            unit = unit_match.group(0).strip()
            street = street[:unit_match.start()].strip()
        parsed = {
            'street': street,
            'unit': unit,
            'city': fallback.group('city').strip(),
            'state': fallback.group('state').upper(),
            'zip': fallback.group('zip')
        }
        print(f"Step 3: Parsed with fallback: {parsed}")
        return parsed

    print("Step 3: All parsers failed — could not extract address components.")
    return None


if __name__ == '__main__':
    test_addresses = [
        "123 Main St, Austin, TX 78701",
        "2124 E 6th St Unit 103, Austin, TX 78702",
        "1700 Willow Creek Dr Unit 154, Austin, TX 78741",
        "632 Ralph Ablanedo Dr Ste 200, Austin, TX 78748",
        "10901 N Lamar Blvd Ste C304, Austin, TX 78753",
        "512 W Martin Luther King Jr Blvd, Austin, TX 78701",
        "2901 S Capital Of Texas Hwy, Austin, TX 78746",
        "12233 Ranch Road 620 N, Austin, TX 78750",
        "6800 W Gate Blvd, Austin, TX 78745",
        "100 Congress Ave Ste 2000, Austin, TX 78701",
        "456 Oak Avenue, Dallas, TX 75201-1234",
        "789 Pine Ln Austin TX 78704",
        "",
        None
    ]

    for addr in test_addresses:
        result = clean_address(addr)
        print(f"Result: {result}\n")

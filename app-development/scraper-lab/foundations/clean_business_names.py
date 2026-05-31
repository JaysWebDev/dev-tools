
import re

# Legal suffixes — safe to remove (company structure, not identity)
LEGAL_SUFFIXES = [
    r'\bInc\.?$', r'\bCorp\.?$', r'\bLtd\.?$', r'\bLLC\.?$', r'\bL\.L\.C\.?$',
    r'\bCo\.?$', r'\bCompany$', r'\bGroup$', r'\bGroupe?$',
    r'\bAssociates?$', r'\bPartners?$', r'\bEnterprises?$', r'\bHoldings?$',
    r'\bInternational$', r'\bGlobal$',
]

# Meaningful words — part of the business identity, NEVER remove
MEANINGFUL_WORDS = {
    'flowers', 'flower', 'florist', 'florists', 'floral',
    'bakery', 'bakeries', 'garden', 'gardens', 'gardening',
    'boutique', 'boutiques', 'design', 'designs', 'studio', 'studios',
    'shop', 'shops', 'store', 'stores', 'market', 'markets',
    'organics', 'organic', 'fresh', 'bloom', 'blooms', 'petal', 'petals',
    'arrangements', 'arrangement', 'bouquet', 'bouquets',
    'services', 'service', 'solutions', 'solution',
}


def clean_business_name(name):
    """
    Cleans a business name by removing ONLY legal entity suffixes (Inc., LLC, Corp., etc.)
    while preserving meaningful business-identity words like 'Flowers', 'Florist', 'Design'.

    Args:
        name (str): The raw business name string.

    Returns:
        str: The cleaned business name, or None if input is invalid.
    """
    print(f"\n--- Cleaning Business Name: {name} ---")

    if not isinstance(name, str) or not name.strip():
        print("Step 1: Invalid input (not a string or empty).")
        return None

    cleaned = name.strip()
    print(f"Step 1: Trimmed whitespace: '{cleaned}'")

    # Remove only legal suffixes — check each word at the end is not a meaningful word first
    suffix_removed = False
    for suffix in LEGAL_SUFFIXES:
        match = re.search(suffix, cleaned, re.IGNORECASE)
        if match:
            # Guard: make sure the matched word is not on the meaningful whitelist
            matched_word = match.group(0).strip().lower().rstrip('.')
            if matched_word not in MEANINGFUL_WORDS:
                cleaned = re.sub(suffix, '', cleaned, flags=re.IGNORECASE).strip().rstrip(',').strip()
                suffix_removed = True
                print(f"Step 2: Removed legal suffix '{suffix}' -> '{cleaned}'")

    if not suffix_removed:
        print("Step 2: No legal suffixes found — name unchanged.")

    # Normalize internal whitespace
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    print(f"Step 3: Normalized internal spaces: '{cleaned}'")

    return cleaned if cleaned else None


if __name__ == '__main__':
    test_names = [
        "Austin Flowers Inc.",         # should keep "Flowers", drop "Inc."
        "The Flower Shop LLC",         # should keep "Flower Shop", drop "LLC"
        "Beautiful Blooms & Co.",      # should drop "Co."
        "Petal Pushers Florist",       # should keep "Florist" (meaningful)
        "Garden Designs Group",        # should drop "Group", keep "Garden Designs"
        "William Paul Floral Design",  # should keep "Design" (meaningful)
        "Freytag's Florist",           # should keep "Florist"
        "Creative Floral Solutions",   # keep "Solutions" (meaningful)
        "A.B.C. Corp.",               # drop "Corp."
        "Bloom & Bud",                # no suffix — unchanged
        "Wildflower Organics",        # keep "Organics" (meaningful)
        "Exquisite Petals Floral Design",  # keep all
        "",
        None
    ]

    for name in test_names:
        result = clean_business_name(name)
        print(f"Result: '{result}'\n")

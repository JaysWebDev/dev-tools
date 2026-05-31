
import re
import html

def clean_text(text_string):
    """
    Cleans a text string by removing HTML entities and normalizing whitespace.

    Args:
        text_string (str): The raw text string.

    Returns:
        str: The cleaned text string.
    """
    print(f"\n--- Cleaning Text: {text_string} ---")

    if not isinstance(text_string, str) or not text_string.strip():
        print("Step 1: Invalid input (not a string or empty).")
        return None

    # Step 1: Decode HTML entities (e.g., &amp; to &)
    decoded_text = html.unescape(text_string)
    print(f"Step 1: Decoded HTML entities: {decoded_text}")

    # Step 2: Remove any remaining HTML tags (if any were not entities)
    # This is a basic regex and might not handle all complex HTML cases
    no_html_tags = re.sub(r'<.*?>', '', decoded_text)
    print(f"Step 2: Removed HTML tags: {no_html_tags}")

    # Step 3: Normalize whitespace (replace multiple spaces/newlines with a single space)
    normalized_whitespace = re.sub(r'\s+', ' ', no_html_tags).strip()
    print(f"Step 3: Normalized whitespace: {normalized_whitespace}")

    return normalized_whitespace

if __name__ == '__main__':
    test_texts = [
        "  Hello &amp; World!  ",
        "This is a test with   extra   spaces.\nAnd newlines.",
        "<p>Some <b>HTML</b> content</p>",
        "No special characters here.",
        "",
        None
    ]

    for text in test_texts:
        if text is None:
            print(f"\n--- Cleaning Text: None ---")
            print("Step 1: Input is None.")
            cleaned = clean_text(text)
        else:
            cleaned = clean_text(text)
        print(f"Result: '{cleaned}'")

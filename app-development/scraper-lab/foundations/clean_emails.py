
import re

def clean_email(email_address):
    """
    Validates and standardizes an email address.

    Args:
        email_address (str): The raw email address string.

    Returns:
        str: The standardized email address, or None if invalid.
    """
    print(f"\n--- Cleaning Email: {email_address} ---")

    if not isinstance(email_address, str) or not email_address.strip():
        print("Step 1: Invalid input (not a string or empty).")
        return None

    cleaned_email = email_address.strip().lower()
    print(f"Step 1: Trimmed whitespace and lowercased: {cleaned_email}")

    # A more robust regex for email validation (RFC 5322 compliant, but simplified for common use)
    # This regex is a balance between strictness and practicality.
    email_regex = re.compile(r"^[a-z0-9!#$%&'*+/=?^_`{|}~-]+(?:\.[a-z0-9!#$%&'*+/=?^_`{|}~-]+)*@(?:[a-z0-9](?:[a-z0-9-]*[a-z0-9])?\.)+[a-z0-9](?:[a-z0-9-]*[a-z0-9])?$")

    if email_regex.match(cleaned_email):
        print(f"Step 2: Email format is valid.")
        return cleaned_email
    else:
        print(f"Step 2: Email format is invalid.")
        return None

if __name__ == '__main__':
    test_emails = [
        "Test.User@Example.com",
        "another_email123@sub.domain.co.uk",
        "invalid-email",
        "user@.com",
        "user@domain",
        "",
        None
    ]

    for email in test_emails:
        if email is None:
            print(f"\n--- Cleaning Email: None ---")
            print("Step 1: Input is None.")
            cleaned = clean_email(email)
        else:
            cleaned = clean_email(email)
        print(f"Result: {cleaned}")


import re

def clean_phone_number(phone_number):
    """
    Cleans and standardizes a phone number to the format (XXX) XXX-XXXX.

    Args:
        phone_number (str): The raw phone number string.

    Returns:
        str: The standardized phone number, or None if invalid.
    """
    print(f"\n--- Cleaning Phone Number: {phone_number} ---")

    if not isinstance(phone_number, str) or not phone_number.strip():
        print("Step 1: Invalid input (not a string or empty).")
        return None

    # Remove all non-digit characters
    digits_only = re.sub(r'\D', '', phone_number)
    print(f"Step 1: Digits only: {digits_only}")

    # Check for valid length (10 digits for US numbers)
    if len(digits_only) == 10:
        # Format as (XXX) XXX-XXXX
        cleaned_number = f"({digits_only[0:3]}) {digits_only[3:6]}-{digits_only[6:10]}"
        print(f"Step 2: Formatted: {cleaned_number}")
        return cleaned_number
    elif len(digits_only) == 11 and digits_only.startswith('1'):
        # Handle 11-digit numbers starting with '1' (e.g., +1-XXX-XXX-XXXX)
        cleaned_number = f"({digits_only[1:4]}) {digits_only[4:7]}-{digits_only[7:11]}"
        print(f"Step 2: Formatted (11-digit): {cleaned_number}")
        return cleaned_number
    else:
        print(f"Step 2: Invalid length after digit extraction. Original: {phone_number}, Digits: {digits_only}")
        return None

if __name__ == '__main__':
    # Example Usage
    test_numbers = [
        "(555) 123-4567",
        "555-123-4567",
        "555.123.4567",
        "5551234567",
        "+1 555 123 4567",
        "1-555-123-4567",
        "(555) 123-45", # Invalid
        "abc-123-defg", # Invalid
        "", # Invalid
        None # Invalid
    ]

    for num in test_numbers:
        if num is None:
            print(f"\n--- Cleaning Phone Number: None ---")
            print("Step 1: Input is None.")
            cleaned = clean_phone_number(num)
        else:
            cleaned = clean_phone_number(num)
        print(f"Result: {cleaned}")


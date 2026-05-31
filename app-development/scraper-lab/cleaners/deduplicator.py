
import pandas as pd
from rapidfuzz import fuzz


class Deduplicator:
    """
    Identifies duplicate business listings using fuzzy matching on cleaned names
    and phone numbers as a secondary signal.

    Adds two columns to the DataFrame:
        is_duplicate (bool): True if the record is a likely duplicate of an earlier one.
        duplicate_of (int or None): Row index of the original record it duplicates.
    """

    def __init__(self, threshold=85):
        """
        Args:
            threshold (int): Minimum fuzz.ratio score (0–100) to consider two names duplicates.
        """
        self.threshold = threshold

    def find_duplicates(self, df, name_col='name_cleaned', phone_col='phone_cleaned'):
        """
        Compare all record pairs and return a list of duplicate relationships.

        Args:
            df (pd.DataFrame): Cleaned records.
            name_col (str): Column to fuzzy-match on.
            phone_col (str): Secondary signal column (exact match boosts confidence).

        Returns:
            list of (idx_a, idx_b, name_score, is_phone_match): duplicate pairs.
        """
        duplicates = []
        names = df[name_col].fillna('').tolist()
        phones = df[phone_col].fillna('') if phone_col in df.columns else [''] * len(df)
        if hasattr(phones, 'tolist'):
            phones = phones.tolist()

        for i in range(len(names)):
            for j in range(i + 1, len(names)):
                if not names[i] or not names[j]:
                    continue
                name_score = fuzz.ratio(names[i].lower(), names[j].lower())
                phone_match = bool(phones[i] and phones[j] and phones[i] == phones[j])

                # Duplicate if names are similar enough, OR names somewhat similar + same phone
                if name_score >= self.threshold or (name_score >= 70 and phone_match):
                    duplicates.append((i, j, name_score, phone_match))

        return duplicates

    def flag_duplicates(self, df, name_col='name_cleaned', phone_col='phone_cleaned'):
        """
        Add is_duplicate and duplicate_of columns to the DataFrame.
        The first occurrence of a duplicate group is kept as original.

        Args:
            df (pd.DataFrame): Cleaned records.

        Returns:
            pd.DataFrame: Original DataFrame with two new columns appended.
        """
        df = df.copy()
        df['is_duplicate'] = False
        df['duplicate_of'] = None

        pairs = self.find_duplicates(df, name_col=name_col, phone_col=phone_col)

        # Track which indices have already been marked as duplicates
        flagged = set()
        for idx_a, idx_b, score, phone_match in pairs:
            if idx_b not in flagged:
                df.at[idx_b, 'is_duplicate'] = True
                df.at[idx_b, 'duplicate_of'] = idx_a
                flagged.add(idx_b)
                print(f"  [dedup] Row {idx_b} is duplicate of row {idx_a} "
                      f"(name_score={score}, phone_match={phone_match})")

        return df


if __name__ == '__main__':
    data = [
        {'name_cleaned': 'Austin Flowers', 'phone_cleaned': '(512) 123-4567'},
        {'name_cleaned': 'Austin Flower',  'phone_cleaned': '(512) 123-4567'},  # near-duplicate
        {'name_cleaned': 'Bloom & Bud',    'phone_cleaned': '(512) 999-0000'},
        {'name_cleaned': 'Bloom and Bud',  'phone_cleaned': '(512) 888-1111'},  # name match only
    ]
    df = pd.DataFrame(data)
    dedup = Deduplicator(threshold=85)
    result = dedup.flag_duplicates(df)
    print(result[['name_cleaned', 'phone_cleaned', 'is_duplicate', 'duplicate_of']])

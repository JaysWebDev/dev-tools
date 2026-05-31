

class DataQualityScorer:
    """
    Scores each record 0–100 based on completeness and cleanliness of cleaned fields.

    Scoring:
        Base score: 100
        Deductions (missing cleaned fields):
            -20  phone_cleaned missing
            -20  address (street_cleaned) missing
            -15  name_cleaned missing
            -10  website_cleaned missing
            -10  email_cleaned missing
        Bonus:
            +10  if name_cleaned, phone_cleaned, AND street_cleaned all present

    Final score is clamped to [0, 100].
    """

    DEDUCTIONS = {
        'phone_cleaned': 20,
        'street_cleaned': 20,
        'name_cleaned': 15,
        'website_cleaned': 10,
        'email_cleaned': 10,
    }
    COMPLETENESS_BONUS = 10
    COMPLETENESS_FIELDS = ('name_cleaned', 'phone_cleaned', 'street_cleaned')

    def score_record(self, record):
        """
        Score a single record (dict or Series).

        Args:
            record: dict-like with cleaned field keys.

        Returns:
            int: Quality score 0–100.
        """
        score = 100

        for field, deduction in self.DEDUCTIONS.items():
            value = record.get(field)
            if value is None or (isinstance(value, float) and str(value) == 'nan') or str(value).strip() == '' or str(value) == 'nan':
                score -= deduction

        # Completeness bonus
        if all(
            record.get(f) and str(record.get(f)).strip() not in ('', 'nan', 'None')
            for f in self.COMPLETENESS_FIELDS
        ):
            score += self.COMPLETENESS_BONUS

        return max(0, min(100, score))

    def score_dataframe(self, df):
        """
        Score all records in a DataFrame.

        Args:
            df (pd.DataFrame): DataFrame with cleaned fields.

        Returns:
            pd.Series: Quality scores for each row.
        """
        return df.apply(lambda row: self.score_record(row.to_dict()), axis=1)

    def summary(self, scores):
        """
        Compute summary stats from a Series of scores.

        Returns:
            dict with mean, min, max, pct_above_70.
        """
        total = len(scores)
        return {
            'mean_score': round(float(scores.mean()), 1),
            'min_score': int(scores.min()),
            'max_score': int(scores.max()),
            'pct_above_70': round(float((scores >= 70).sum() / total * 100), 1) if total > 0 else 0.0,
        }


if __name__ == '__main__':
    import pandas as pd

    records = [
        {'name_cleaned': 'Austin Flowers', 'phone_cleaned': '(512) 123-4567',
         'street_cleaned': '123 Main St', 'website_cleaned': None, 'email_cleaned': None},
        {'name_cleaned': None, 'phone_cleaned': None,
         'street_cleaned': None, 'website_cleaned': None, 'email_cleaned': None},
        {'name_cleaned': 'Bloom', 'phone_cleaned': '(512) 999-0000',
         'street_cleaned': '456 Oak Ave', 'website_cleaned': 'https://bloom.com', 'email_cleaned': 'hi@bloom.com'},
    ]
    df = pd.DataFrame(records)
    scorer = DataQualityScorer()
    df['quality_score'] = scorer.score_dataframe(df)
    print(df[['name_cleaned', 'phone_cleaned', 'quality_score']])
    print("\nSummary:", scorer.summary(df['quality_score']))

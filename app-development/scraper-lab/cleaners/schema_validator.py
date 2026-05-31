
import os
import pandas as pd
import pandera.pandas as pa
from pandera.pandas import Column, Check, DataFrameSchema


FLORIST_SCHEMA = DataFrameSchema(
    {
        'name_cleaned': Column(str, nullable=True, coerce=True),
        'phone_cleaned': Column(str, nullable=True, coerce=True, checks=[
            Check(lambda s: s.dropna().str.match(r'^\(\d{3}\) \d{3}-\d{4}$').all(),
                  error="phone_cleaned must be in (XXX) XXX-XXXX format")
        ]),
        'street_cleaned': Column(str, nullable=True, coerce=True),
        'city_cleaned':   Column(str, nullable=True, coerce=True),
        'state_cleaned':  Column(str, nullable=True, coerce=True, checks=[
            Check(lambda s: s.dropna().str.match(r'^[A-Z]{2}$').all(),
                  error="state_cleaned must be 2-letter uppercase abbreviation")
        ]),
        'zip_cleaned': Column(str, nullable=True, coerce=True, checks=[
            Check(lambda s: s.dropna().str.match(r'^\d{5}(?:-\d{4})?$').all(),
                  error="zip_cleaned must be 5 or 5-4 digit format")
        ]),
        'quality_score': Column(int, nullable=False, coerce=True, checks=[
            Check.in_range(0, 100, error="quality_score must be between 0 and 100")
        ]),
    },
    coerce=True,
    strict=False,  # Allow extra columns
)


def validate(df):
    """
    Validate a cleaned DataFrame against the florist schema.

    Args:
        df (pd.DataFrame): Cleaned DataFrame.

    Returns:
        tuple: (is_valid: bool, report: dict)
    """
    report = {'is_valid': False, 'errors': [], 'rows_checked': len(df)}

    # Only validate columns that are present
    present_cols = {k: v for k, v in FLORIST_SCHEMA.columns.items() if k in df.columns}
    schema = DataFrameSchema(present_cols, coerce=True, strict=False)

    try:
        schema.validate(df, lazy=True)
        report['is_valid'] = True
        print("  [schema] Validation passed.")
    except pa.errors.SchemaErrors as e:
        failure_df = e.failure_cases
        errors = failure_df[['schema_context', 'column', 'check', 'failure_case']].to_dict('records')
        report['errors'] = [
            {
                'column': str(err.get('column')),
                'check': str(err.get('check')),
                'failure_case': str(err.get('failure_case')),
            }
            for err in errors[:20]
        ]
        report['error_count'] = len(failure_df)
        print(f"  [schema] Validation failed — {len(errors)} issue(s) found.")

    return report['is_valid'], report


if __name__ == '__main__':
    import json
    data = [
        {'name_cleaned': 'Austin Flowers', 'phone_cleaned': '(512) 123-4567',
         'street_cleaned': '123 Main St', 'city_cleaned': 'Austin',
         'state_cleaned': 'TX', 'zip_cleaned': '78701', 'quality_score': 85},
        {'name_cleaned': 'Bloom', 'phone_cleaned': '5121234567',
         'street_cleaned': None, 'city_cleaned': 'Austin',
         'state_cleaned': 'Texas', 'zip_cleaned': '787', 'quality_score': 40},
    ]
    df = pd.DataFrame(data)
    is_valid, report = validate(df)
    print(json.dumps(report, indent=2))

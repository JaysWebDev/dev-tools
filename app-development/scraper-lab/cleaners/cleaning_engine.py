
import sys
import os
import pandas as pd
import json
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '01_foundations'))

from clean_phone_numbers import clean_phone_number
from clean_addresses import clean_address
from clean_business_names import clean_business_name
from clean_urls import clean_url
from clean_emails import clean_email
from clean_text import clean_text
from quality_scorer import DataQualityScorer


class CleaningEngine:
    """
    Orchestrates the full data cleaning pipeline:
    1. Cleans each field using dedicated cleaner functions
    2. Scores record quality (0–100)
    3. Flags duplicates (if deduplicator is available)
    4. Validates schema (if validator is available)
    5. Exports to multiple formats
    6. Generates a JSON report
    """

    def __init__(self, raw_df, config=None):
        self.raw_df = raw_df
        self.cleaned_df = None
        self.report = {}
        self.config = config or {}
        self._scorer = DataQualityScorer()

    # ------------------------------------------------------------------
    # Cleaning
    # ------------------------------------------------------------------

    def clean_data(self):
        """Apply all cleaning steps and return the cleaned DataFrame."""
        print("\n--- Starting Data Cleaning Process ---")
        self.cleaned_df = self.raw_df.copy()
        stats = {'total_rows': len(self.raw_df), 'cleaned_columns': {}}

        # Business names
        print("\nCleaning Business Names...")
        self.cleaned_df['name_cleaned'] = self.cleaned_df['name'].apply(clean_business_name)
        stats['cleaned_columns']['name'] = int(self.cleaned_df['name_cleaned'].notnull().sum())

        # Phone numbers
        print("\nCleaning Phone Numbers...")
        self.cleaned_df['phone_cleaned'] = self.cleaned_df['phone'].apply(clean_phone_number)
        stats['cleaned_columns']['phone'] = int(self.cleaned_df['phone_cleaned'].notnull().sum())

        # Addresses — expand dict result into separate columns
        print("\nCleaning Addresses...")
        address_components = self.cleaned_df['address'].apply(clean_address)
        empty = {'street': None, 'unit': None, 'city': None, 'state': None, 'zip': None}
        address_list = [a if isinstance(a, dict) else empty for a in address_components]
        address_df = pd.DataFrame(address_list).rename(columns={
            'street': 'street_cleaned',
            'unit': 'unit_cleaned',
            'city': 'city_cleaned',
            'state': 'state_cleaned',
            'zip': 'zip_cleaned',
        })
        self.cleaned_df = pd.concat(
            [self.cleaned_df.reset_index(drop=True), address_df.reset_index(drop=True)], axis=1
        )
        stats['cleaned_columns']['address'] = {
            col: int(address_df[col].notnull().sum()) for col in address_df.columns
        }

        # URLs
        print("\nCleaning URLs...")
        self.cleaned_df['website_cleaned'] = self.cleaned_df['website'].apply(clean_url)
        stats['cleaned_columns']['website'] = int(self.cleaned_df['website_cleaned'].notnull().sum())

        # Emails
        print("\nCleaning Emails...")
        self.cleaned_df['email_cleaned'] = self.cleaned_df['email'].apply(clean_email)
        stats['cleaned_columns']['email'] = int(self.cleaned_df['email_cleaned'].notnull().sum())

        # Quality scoring
        print("\nScoring Data Quality...")
        self.cleaned_df['quality_score'] = self._scorer.score_dataframe(self.cleaned_df)
        score_summary = self._scorer.summary(self.cleaned_df['quality_score'])
        stats['quality_scores'] = score_summary
        print(f"  Mean score: {score_summary['mean_score']} | "
              f"Min: {score_summary['min_score']} | Max: {score_summary['max_score']} | "
              f"Above 70: {score_summary['pct_above_70']}%")

        # Deduplication (optional — requires deduplicator module)
        dedup_threshold = self.config.get('cleaning', {}).get('dedup_threshold', 85)
        try:
            from deduplicator import Deduplicator
            print(f"\nRunning Deduplication (threshold={dedup_threshold})...")
            dedup = Deduplicator(threshold=dedup_threshold)
            self.cleaned_df = dedup.flag_duplicates(self.cleaned_df, name_col='name_cleaned')
            dup_count = int(self.cleaned_df['is_duplicate'].sum())
            stats['duplicates_found'] = dup_count
            print(f"  Duplicates flagged: {dup_count}")
        except ImportError:
            pass

        # Schema validation (optional — requires schema_validator module)
        try:
            from schema_validator import validate
            print("\nValidating Schema...")
            is_valid, val_report = validate(self.cleaned_df)
            stats['schema_validation'] = val_report
            print(f"  Schema valid: {is_valid}")
        except ImportError:
            pass

        self.report = stats
        print("\n--- Data Cleaning Process Complete ---")
        return self.cleaned_df

    # ------------------------------------------------------------------
    # Export
    # ------------------------------------------------------------------

    def export_data(self, base_path, formats=None):
        """
        Export cleaned DataFrame to one or more formats.

        Supported formats: csv, json, parquet, excel, feather
        Compression: append '.gz' to format string (e.g. 'csv.gz')
        """
        if formats is None:
            formats = self.config.get('output', {}).get('formats', ['csv', 'json'])

        for fmt in formats:
            compress = fmt.endswith('.gz')
            base_fmt = fmt.rstrip('.gz') if compress else fmt
            ext = f"{base_fmt}.gz" if compress else base_fmt
            output_path = f"{base_path}.{ext}"
            print(f"Exporting cleaned data to: {output_path}")

            try:
                if base_fmt == 'csv':
                    compression = 'gzip' if compress else None
                    self.cleaned_df.to_csv(output_path, index=False, compression=compression)
                elif base_fmt == 'json':
                    self.cleaned_df.to_json(output_path, orient='records', indent=4)
                elif base_fmt == 'parquet':
                    self.cleaned_df.to_parquet(output_path, index=False)
                elif base_fmt in ('excel', 'xlsx'):
                    self.cleaned_df.to_excel(output_path, index=False)
                elif base_fmt == 'feather':
                    self.cleaned_df.to_feather(output_path)
                else:
                    print(f"  Unknown format '{fmt}' — skipping.")
            except Exception as e:
                print(f"  Export failed for '{fmt}': {e}")

    # ------------------------------------------------------------------
    # Report
    # ------------------------------------------------------------------

    def generate_report(self, output_path):
        """Write a JSON cleaning report to output_path."""
        print(f"\nGenerating cleaning report: {output_path}")

        def _convert(obj):
            if isinstance(obj, dict):
                return {k: _convert(v) for k, v in obj.items()}
            elif isinstance(obj, (list, tuple)):
                return [_convert(i) for i in obj]
            elif hasattr(obj, 'item'):
                return obj.item()
            return obj

        report_data = {
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'stats': _convert(self.report),
        }
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, 'w') as f:
            json.dump(report_data, f, indent=4)


if __name__ == '__main__':
    dummy_data = [
        {'name': 'Austin Flowers Inc.', 'phone': '512-123-4567',
         'address': '123 Main St, Austin, TX 78701',
         'website': 'www.austinflowers.com?utm_source=google',
         'email': 'info@austinflowers.com'},
        {'name': 'The Flower Shop LLC', 'phone': '(512) 987-6543',
         'address': '2124 E 6th St Unit 103, Austin, TX 78702',
         'website': None, 'email': None},
    ]
    df = pd.DataFrame(dummy_data)
    engine = CleaningEngine(df)
    cleaned = engine.clean_data()
    print("\nCleaned Data:")
    print(cleaned[['name', 'name_cleaned', 'phone', 'phone_cleaned', 'street_cleaned', 'unit_cleaned', 'quality_score']])

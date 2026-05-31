#!/usr/bin/env python3
"""
Enhanced File Organizer v2.0
Advanced file organization tool with metadata analysis and intelligent categorization
"""

import os
import shutil
import json
import hashlib
import mimetypes
import subprocess
import argparse
import logging
from pathlib import Path
from datetime import datetime
from collections import defaultdict, Counter
import re

class EnhancedFileOrganizer:
    def __init__(self, target_dir, output_dir=None, dry_run=False):
        self.target_dir = Path(target_dir).resolve()
        self.output_dir = Path(output_dir) if output_dir else self.target_dir / "organized"
        self.dry_run = dry_run
        self.file_stats = defaultdict(list)
        self.duplicate_groups = []
        self.metadata_cache = {}

        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(self.target_dir / 'organization.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)

        # File type categories
        self.categories = {
            'documents': {
                'extensions': ['.pdf', '.doc', '.docx', '.txt', '.rtf', '.odt', '.xls', '.xlsx', '.ppt', '.pptx'],
                'keywords': ['report', 'document', 'letter', 'resume', 'cv']
            },
            'images': {
                'extensions': ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.svg', '.webp'],
                'keywords': ['photo', 'image', 'picture', 'screenshot']
            },
            'videos': {
                'extensions': ['.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm', '.m4v'],
                'keywords': ['video', 'movie', 'clip', 'recording']
            },
            'audio': {
                'extensions': ['.mp3', '.wav', '.flac', '.aac', '.ogg', '.wma', '.m4a'],
                'keywords': ['audio', 'music', 'sound', 'song']
            },
            'code': {
                'extensions': ['.py', '.js', '.html', '.css', '.java', '.cpp', '.c', '.h', '.php', '.rb', '.go'],
                'keywords': ['source', 'script', 'code', 'program']
            },
            'archives': {
                'extensions': ['.zip', '.rar', '.7z', '.tar', '.gz', '.bz2', '.xz'],
                'keywords': ['archive', 'compressed', 'backup']
            },
            'data': {
                'extensions': ['.json', '.xml', '.csv', '.sql', '.db', '.sqlite'],
                'keywords': ['data', 'database', 'export']
            }
        }

    def get_file_hash(self, filepath):
        """Generate MD5 hash for duplicate detection"""
        hash_md5 = hashlib.md5()
        try:
            with open(filepath, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
            return hash_md5.hexdigest()
        except (IOError, PermissionError):
            return None

    def extract_metadata(self, filepath):
        """Extract metadata using exiftool"""
        if filepath in self.metadata_cache:
            return self.metadata_cache[filepath]

        try:
            result = subprocess.run(
                ['exiftool', '-json', str(filepath)],
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode == 0:
                metadata = json.loads(result.stdout)[0]
                self.metadata_cache[filepath] = metadata
                return metadata
        except (subprocess.TimeoutExpired, json.JSONDecodeError, FileNotFoundError):
            pass

        return {}

    def clean_filename(self, filename):
        """Clean and normalize filename"""
        # Remove special characters and normalize spaces
        clean = re.sub(r'[^\w\-_\.]', '_', filename)
        clean = re.sub(r'_+', '_', clean)
        clean = clean.strip('_')
        return clean

    def categorize_file(self, filepath):
        """Intelligent file categorization"""
        filepath = Path(filepath)
        filename_lower = filepath.name.lower()
        extension = filepath.suffix.lower()

        # Check by extension first
        for category, info in self.categories.items():
            if extension in info['extensions']:
                return category

        # Check by filename keywords
        for category, info in self.categories.items():
            for keyword in info['keywords']:
                if keyword in filename_lower:
                    return category

        # Check by MIME type
        mime_type, _ = mimetypes.guess_type(str(filepath))
        if mime_type:
            main_type = mime_type.split('/')[0]
            mime_mapping = {
                'image': 'images',
                'video': 'videos',
                'audio': 'audio',
                'text': 'documents',
                'application': 'documents'
            }
            if main_type in mime_mapping:
                return mime_mapping[main_type]

        return 'miscellaneous'

    def scan_directory(self):
        """Recursively scan directory and collect file information"""
        self.logger.info(f"Scanning directory: {self.target_dir}")

        file_hashes = defaultdict(list)
        total_files = 0

        for root, dirs, files in os.walk(self.target_dir):
            for file in files:
                filepath = Path(root) / file
                if filepath.is_file():
                    total_files += 1

                    # Basic file info
                    stat_info = filepath.stat()
                    file_info = {
                        'original_path': str(filepath),
                        'filename': file,
                        'size': stat_info.st_size,
                        'modified': datetime.fromtimestamp(stat_info.st_mtime),
                        'extension': filepath.suffix.lower(),
                        'category': self.categorize_file(filepath),
                        'hash': self.get_file_hash(filepath),
                        'metadata': self.extract_metadata(filepath)
                    }

                    # Track duplicates
                    if file_info['hash']:
                        file_hashes[file_info['hash']].append(file_info)

                    self.file_stats[file_info['category']].append(file_info)

        # Identify duplicate groups
        self.duplicate_groups = [files for files in file_hashes.values() if len(files) > 1]

        self.logger.info(f"Scan complete: {total_files} files found")
        self.logger.info(f"Categories: {dict([(k, len(v)) for k, v in self.file_stats.items()])}")
        self.logger.info(f"Duplicate groups: {len(self.duplicate_groups)}")

    def generate_unique_name(self, category_dir, filename, metadata=None):
        """Generate unique filename based on metadata and content"""
        filepath = Path(filename)
        base_name = filepath.stem
        extension = filepath.suffix

        # Try to use metadata for better naming
        if metadata:
            # For images: use date taken if available
            if 'DateTimeOriginal' in metadata:
                try:
                    date_str = metadata['DateTimeOriginal'].replace(':', '-').replace(' ', '_')
                    base_name = f"IMG_{date_str}"
                except:
                    pass

            # For documents: use title if available
            elif 'Title' in metadata and metadata['Title'].strip():
                base_name = self.clean_filename(metadata['Title'])

            # For videos: use creation date
            elif 'CreateDate' in metadata:
                try:
                    date_str = metadata['CreateDate'].replace(':', '-').replace(' ', '_')
                    base_name = f"VID_{date_str}"
                except:
                    pass

        # Clean the base name
        base_name = self.clean_filename(base_name)

        # Ensure uniqueness
        counter = 1
        new_filename = f"{base_name}{extension}"
        while (category_dir / new_filename).exists():
            new_filename = f"{base_name}_{counter:03d}{extension}"
            counter += 1

        return new_filename

    def organize_files(self):
        """Organize files into categorized directories"""
        if not self.file_stats:
            self.logger.error("No files scanned. Run scan_directory() first.")
            return

        self.logger.info(f"Organizing files to: {self.output_dir}")

        # Create output directory structure
        if not self.dry_run:
            self.output_dir.mkdir(exist_ok=True)

        # Create duplicate analysis report
        duplicate_report = []

        for category, files in self.file_stats.items():
            category_dir = self.output_dir / category

            if not self.dry_run:
                category_dir.mkdir(exist_ok=True)

            self.logger.info(f"Processing {len(files)} files in category: {category}")

            for file_info in files:
                original_path = Path(file_info['original_path'])

                # Generate new filename
                new_filename = self.generate_unique_name(
                    category_dir,
                    original_path.name,
                    file_info['metadata']
                )

                new_path = category_dir / new_filename

                if self.dry_run:
                    self.logger.info(f"WOULD MOVE: {original_path} -> {new_path}")
                else:
                    try:
                        shutil.copy2(original_path, new_path)
                        self.logger.info(f"MOVED: {original_path} -> {new_path}")
                    except Exception as e:
                        self.logger.error(f"Failed to move {original_path}: {e}")

        # Generate reports
        self.generate_reports()

    def generate_reports(self):
        """Generate organization and duplicate reports"""
        reports_dir = self.output_dir / "reports"
        if not self.dry_run:
            reports_dir.mkdir(exist_ok=True)

        # Organization summary
        summary = {
            'scan_date': datetime.now().isoformat(),
            'source_directory': str(self.target_dir),
            'output_directory': str(self.output_dir),
            'categories': {cat: len(files) for cat, files in self.file_stats.items()},
            'total_files': sum(len(files) for files in self.file_stats.values()),
            'duplicate_groups': len(self.duplicate_groups),
            'total_duplicates': sum(len(group) for group in self.duplicate_groups)
        }

        # Duplicate report
        duplicate_report = []
        for group in self.duplicate_groups:
            duplicate_info = {
                'hash': group[0]['hash'],
                'size': group[0]['size'],
                'files': [f['original_path'] for f in group],
                'recommended_action': 'Keep first, review others'
            }
            duplicate_report.append(duplicate_info)

        if not self.dry_run:
            # Write summary report
            with open(reports_dir / 'organization_summary.json', 'w') as f:
                json.dump(summary, f, indent=2, default=str)

            # Write duplicate report
            with open(reports_dir / 'duplicates.json', 'w') as f:
                json.dump(duplicate_report, f, indent=2)

            # Write human-readable summary
            with open(reports_dir / 'summary.txt', 'w') as f:
                f.write("=== ENHANCED FILE ORGANIZATION REPORT ===\n\n")
                f.write(f"Scan Date: {summary['scan_date']}\n")
                f.write(f"Source: {summary['source_directory']}\n")
                f.write(f"Output: {summary['output_directory']}\n\n")
                f.write("CATEGORIES:\n")
                for cat, count in summary['categories'].items():
                    f.write(f"  {cat}: {count} files\n")
                f.write(f"\nTOTAL FILES: {summary['total_files']}\n")
                f.write(f"DUPLICATE GROUPS: {summary['duplicate_groups']}\n")
                f.write(f"SPACE WASTED BY DUPLICATES: {sum(group[0]['size'] * (len(group)-1) for group in self.duplicate_groups) / 1024 / 1024:.2f} MB\n")

        self.logger.info("Reports generated successfully")

    def clean_metadata(self, remove_originals=False):
        """Remove metadata from organized files"""
        if not self.output_dir.exists():
            self.logger.error("Output directory doesn't exist. Organize files first.")
            return

        self.logger.info("Starting metadata cleaning...")

        for category_dir in self.output_dir.iterdir():
            if category_dir.is_dir() and category_dir.name != 'reports':
                for filepath in category_dir.rglob('*'):
                    if filepath.is_file():
                        try:
                            # Create backup if not removing originals
                            if not remove_originals:
                                backup_path = filepath.with_suffix(filepath.suffix + '.backup')
                                if not self.dry_run:
                                    shutil.copy2(filepath, backup_path)

                            # Remove metadata
                            if not self.dry_run:
                                subprocess.run(
                                    ['exiftool', '-all=', '-overwrite_original', str(filepath)],
                                    capture_output=True,
                                    check=True
                                )
                                self.logger.info(f"Cleaned metadata: {filepath}")
                        except Exception as e:
                            self.logger.error(f"Failed to clean metadata for {filepath}: {e}")


def main():
    parser = argparse.ArgumentParser(description='Enhanced File Organizer v2.0')
    parser.add_argument('target_dir', help='Directory to organize')
    parser.add_argument('-o', '--output', help='Output directory (default: target_dir/organized)')
    parser.add_argument('-d', '--dry-run', action='store_true', help='Show what would be done without making changes')
    parser.add_argument('-c', '--clean-metadata', action='store_true', help='Remove metadata after organizing')
    parser.add_argument('--remove-originals', action='store_true', help='Remove original files when cleaning metadata')

    args = parser.parse_args()

    # Initialize organizer
    organizer = EnhancedFileOrganizer(
        target_dir=args.target_dir,
        output_dir=args.output,
        dry_run=args.dry_run
    )

    try:
        # Scan directory
        organizer.scan_directory()

        # Organize files
        organizer.organize_files()

        # Clean metadata if requested
        if args.clean_metadata:
            organizer.clean_metadata(remove_originals=args.remove_originals)

        print("\n=== ORGANIZATION COMPLETE ===")
        print(f"Check the reports directory for detailed analysis")

    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
    except Exception as e:
        print(f"Error: {e}")
        raise


if __name__ == "__main__":
    main()
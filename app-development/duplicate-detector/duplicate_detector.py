#!/usr/bin/env python3
"""
🔍 Advanced Duplicate File Detection System
Comprehensive duplicate detection with size-based filtering and deep analysis
"""

import os
import hashlib
import sys
from pathlib import Path
from collections import defaultdict
import argparse
from datetime import datetime
import json

class DuplicateDetector:
    def __init__(self, min_size=1024):
        """
        Initialize duplicate detector

        Args:
            min_size (int): Minimum file size in bytes to consider (default 1KB)
        """
        self.min_size = min_size
        self.size_groups = defaultdict(list)
        self.hash_groups = defaultdict(list)
        self.stats = {
            'total_files': 0,
            'total_size': 0,
            'duplicate_groups': 0,
            'duplicate_files': 0,
            'wasted_space': 0,
            'scan_time': 0
        }

    def get_file_hash(self, filepath, chunk_size=8192):
        """Calculate MD5 hash of file"""
        hash_md5 = hashlib.md5()
        try:
            with open(filepath, "rb") as f:
                for chunk in iter(lambda: f.read(chunk_size), b""):
                    hash_md5.update(chunk)
            return hash_md5.hexdigest()
        except (IOError, OSError, PermissionError) as e:
            print(f"⚠️  Error reading {filepath}: {e}")
            return None

    def scan_directory(self, root_path, exclude_dirs=None):
        """
        Scan directory for files and group by size

        Args:
            root_path (str): Root directory to scan
            exclude_dirs (list): Directories to exclude (e.g., ['.git', 'node_modules'])
        """
        if exclude_dirs is None:
            exclude_dirs = ['.git', 'node_modules', '__pycache__', '.venv', 'venv']

        exclude_dirs = set(exclude_dirs)

        print(f"🔍 Scanning directory: {root_path}")
        start_time = datetime.now()

        for root, dirs, files in os.walk(root_path):
            # Remove excluded directories from scan
            dirs[:] = [d for d in dirs if d not in exclude_dirs]

            for filename in files:
                filepath = os.path.join(root, filename)
                try:
                    stat = os.stat(filepath)
                    file_size = stat.st_size

                    # Skip files smaller than minimum size
                    if file_size < self.min_size:
                        continue

                    self.stats['total_files'] += 1
                    self.stats['total_size'] += file_size

                    # Group files by size
                    self.size_groups[file_size].append(filepath)

                    if self.stats['total_files'] % 1000 == 0:
                        print(f"  📊 Processed {self.stats['total_files']:,} files...")

                except (OSError, IOError):
                    # Skip files we can't access
                    continue

        self.stats['scan_time'] = (datetime.now() - start_time).total_seconds()
        print(f"✅ Scan complete: {self.stats['total_files']:,} files in {self.stats['scan_time']:.2f} seconds")

    def find_duplicates(self):
        """Find duplicate files by comparing hashes of same-size files"""
        print("\n🔍 Analyzing potential duplicates...")

        potential_duplicates = {size: paths for size, paths in self.size_groups.items() if len(paths) > 1}

        if not potential_duplicates:
            print("✅ No duplicate files found!")
            return

        print(f"📊 Found {len(potential_duplicates)} size groups with potential duplicates")

        processed = 0
        total_potential = sum(len(paths) for paths in potential_duplicates.values())

        for size, filepaths in potential_duplicates.items():
            # Calculate hashes for files of same size
            for filepath in filepaths:
                file_hash = self.get_file_hash(filepath)
                if file_hash:
                    self.hash_groups[file_hash].append((filepath, size))

                processed += 1
                if processed % 100 == 0:
                    print(f"  📊 Hashed {processed:,}/{total_potential:,} potential duplicates...")

        # Find actual duplicates (same hash)
        duplicate_groups = {h: files for h, files in self.hash_groups.items() if len(files) > 1}

        self.stats['duplicate_groups'] = len(duplicate_groups)

        for file_hash, files in duplicate_groups.items():
            self.stats['duplicate_files'] += len(files)
            # Calculate wasted space (all but one copy)
            file_size = files[0][1]
            self.stats['wasted_space'] += file_size * (len(files) - 1)

        return duplicate_groups

    def format_size(self, bytes_size):
        """Format bytes to human readable size"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes_size < 1024.0:
                return f"{bytes_size:.1f} {unit}"
            bytes_size /= 1024.0
        return f"{bytes_size:.1f} PB"

    def print_report(self, duplicate_groups):
        """Print comprehensive duplicate file report"""
        print(f"\n{'='*60}")
        print(f"🎯 DUPLICATE FILE DETECTION REPORT")
        print(f"{'='*60}")

        # Statistics
        print(f"\n📊 SCAN STATISTICS:")
        print(f"  Total Files Scanned: {self.stats['total_files']:,}")
        print(f"  Total Size Scanned: {self.format_size(self.stats['total_size'])}")
        print(f"  Scan Duration: {self.stats['scan_time']:.2f} seconds")
        print(f"  Minimum File Size: {self.format_size(self.min_size)}")

        if not duplicate_groups:
            print(f"\n✅ NO DUPLICATES FOUND - System is clean!")
            return

        print(f"\n🔍 DUPLICATE ANALYSIS:")
        print(f"  Duplicate Groups: {self.stats['duplicate_groups']:,}")
        print(f"  Total Duplicate Files: {self.stats['duplicate_files']:,}")
        print(f"  Wasted Space: {self.format_size(self.stats['wasted_space'])}")
        print(f"  Space Recovery Potential: {self.format_size(self.stats['wasted_space'])}")

        # Top duplicate groups by wasted space
        sorted_groups = sorted(
            [(h, files) for h, files in duplicate_groups.items()],
            key=lambda x: x[1][0][1] * (len(x[1]) - 1),  # wasted space
            reverse=True
        )

        print(f"\n🎯 TOP DUPLICATE GROUPS (by wasted space):")
        print(f"{'='*60}")

        for i, (file_hash, files) in enumerate(sorted_groups[:10], 1):
            file_size = files[0][1]
            wasted = file_size * (len(files) - 1)

            print(f"\n📁 Group #{i}: {len(files)} copies - Wasted: {self.format_size(wasted)}")
            print(f"   Size per file: {self.format_size(file_size)}")
            print(f"   Hash: {file_hash[:16]}...")

            for filepath, _ in files:
                rel_path = os.path.relpath(filepath)
                if len(rel_path) > 80:
                    rel_path = "..." + rel_path[-77:]
                print(f"   📄 {rel_path}")

        if len(sorted_groups) > 10:
            print(f"\n... and {len(sorted_groups) - 10} more duplicate groups")

    def save_detailed_report(self, duplicate_groups, output_file):
        """Save detailed JSON report"""
        report_data = {
            'scan_timestamp': datetime.now().isoformat(),
            'statistics': self.stats,
            'duplicate_groups': []
        }

        for file_hash, files in duplicate_groups.items():
            file_size = files[0][1]
            wasted_space = file_size * (len(files) - 1)

            group_data = {
                'hash': file_hash,
                'file_count': len(files),
                'file_size': file_size,
                'wasted_space': wasted_space,
                'files': [{'path': filepath, 'size': size} for filepath, size in files]
            }
            report_data['duplicate_groups'].append(group_data)

        with open(output_file, 'w') as f:
            json.dump(report_data, f, indent=2)

        print(f"\n📄 Detailed report saved: {output_file}")

def main():
    parser = argparse.ArgumentParser(description='Advanced Duplicate File Detector')
    parser.add_argument('path', nargs='?', default='.', help='Directory to scan (default: current directory)')
    parser.add_argument('--min-size', type=int, default=1024, help='Minimum file size in bytes (default: 1024)')
    parser.add_argument('--exclude', nargs='*', default=[], help='Directories to exclude from scan')
    parser.add_argument('--output', type=str, help='Output file for detailed JSON report')

    args = parser.parse_args()

    if not os.path.exists(args.path):
        print(f"❌ Error: Path '{args.path}' does not exist")
        sys.exit(1)

    print(f"🔍 Advanced Duplicate File Detection System")
    print(f"{'='*50}")
    print(f"Target Directory: {os.path.abspath(args.path)}")
    print(f"Minimum File Size: {args.min_size} bytes")
    if args.exclude:
        print(f"Excluded Directories: {', '.join(args.exclude)}")

    # Initialize detector
    detector = DuplicateDetector(min_size=args.min_size)

    # Scan directory
    detector.scan_directory(args.path, exclude_dirs=args.exclude)

    # Find duplicates
    duplicate_groups = detector.find_duplicates()

    # Print report
    detector.print_report(duplicate_groups)

    # Save detailed report if requested
    if args.output and duplicate_groups:
        detector.save_detailed_report(duplicate_groups, args.output)

if __name__ == "__main__":
    main()
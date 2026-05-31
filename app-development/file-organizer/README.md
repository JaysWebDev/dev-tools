# Smart File Organizer

Categorizes and moves files by type, removes metadata, and produces a clean organized directory structure.

## Tools

### `smart_organizer.py`
- Categorizes files by extension: video, note, image, file
- Strips EXIF/metadata via exiftool before moving
- Outputs organized subdirectories

### `enhanced_file_organizer.py`
- Extended version with more categories and duplicate handling
- Dry-run mode to preview changes before applying

## Usage

```bash
python smart_organizer.py /path/to/messy/folder
python enhanced_file_organizer.py /path/to/folder --dry-run
```

## Requirements

```bash
# exiftool for metadata stripping
sudo apt install libimage-exiftool-perl
```

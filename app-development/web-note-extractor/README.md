# Web Note Extractor

Chrome extension (Manifest V3) — save any webpage as a clean text file or PDF with one click.

Automatically scrolls to load lazy content, strips navigation/ads for cleaner output, and saves files with smart filenames including the page title and date.

## Features

- **Extract as Text** — scrolls the full page, extracts readable content, saves as `.txt` in a `WebNotes/` folder
- **Save as PDF** — opens the print dialog pre-configured for clean PDF output
- **Extract Both** — does both in one click
- Works on any website
- Falls back to full body text if no semantic content containers are found

## Install

1. Clone or download this folder
2. Open Chrome → `chrome://extensions`
3. Enable **Developer mode** (top right)
4. Click **Load unpacked** → select this folder

## Output

Text files are saved to your default downloads folder under `WebNotes/`:
```
WebNotes/
  Page_Title_2024-01-15.txt
```

Each file includes the source URL, title, and extraction date at the top.

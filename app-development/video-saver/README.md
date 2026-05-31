# Video Saver

Chrome extension that intercepts video streams and saves them locally with one click.

## Features

- Toggle on/off from the popup
- Intercepts HLS/MP4/WebM streams via background service worker
- Tracks save stats per session

## Install

1. Open `chrome://extensions/`
2. Enable **Developer mode**
3. Click **Load unpacked** → select this folder

## Files

| File | Purpose |
|------|---------|
| `manifest.json` | Extension manifest (Manifest V3) |
| `background.js` | Service worker — intercepts network requests |
| `popup.html/js` | Extension popup UI |

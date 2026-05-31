// Video Auto Saver — background service worker
// Monitors network requests for video files and auto-downloads them

let enabled = false;
let downloadedUrls = new Set();
let stats = { detected: 0, downloaded: 0, failed: 0, videos: [] };

// Video file extensions
const VIDEO_EXTENSIONS = /\.(mp4|webm|mkv|avi|mov|m4v|flv|wmv|mpg|mpeg|ts|m3u8)(\?|$)/i;

// Video MIME types to match in URLs or content-type
const VIDEO_MIME_PATTERNS = [
  'video/mp4', 'video/webm', 'video/x-matroska', 'video/avi',
  'video/quicktime', 'video/x-m4v', 'video/x-flv', 'video/x-ms-wmv',
  'video/mpeg', 'video/mp2t'
];

// URL patterns that indicate video hosting/streaming
const VIDEO_HOST_PATTERNS = [
  /panopto\.com.*\/Embed/i,
  /kaltura\.com.*\/p\//i,
  /brightcove/i,
  /wistia\.com/i,
  /vimeo.*player/i,
  /cloudfront.*\.mp4/i,
  /amazonaws.*\.mp4/i,
  /bbcswebdav.*video/i,
  /learn\.bu\.edu.*\/video/i
];

// URLs to ignore (tracking pixels, ads, tiny files)
const IGNORE_PATTERNS = [
  /google-analytics/i,
  /doubleclick/i,
  /facebook.*pixel/i,
  /\.gif(\?|$)/i,
  /\.js(\?|$)/i
];

// Load saved state
chrome.storage.local.get(['videoSaverEnabled'], (result) => {
  enabled = result.videoSaverEnabled || false;
  if (enabled) startMonitoring();
});

// Listen for messages from popup
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === 'toggle') {
    enabled = request.enabled;
    chrome.storage.local.set({ videoSaverEnabled: enabled });
    if (enabled) {
      startMonitoring();
    }
    sendResponse({ enabled });
  } else if (request.action === 'getStatus') {
    sendResponse({ enabled, stats });
  } else if (request.action === 'clearStats') {
    stats = { detected: 0, downloaded: 0, failed: 0, videos: [] };
    downloadedUrls.clear();
    sendResponse({ success: true });
  } else if (request.action === 'scanPage') {
    // Manually scan current tab for videos
    scanTabForVideos(request.tabId);
    sendResponse({ success: true });
  }
  return true;
});

// Monitor network requests for video content
function startMonitoring() {
  // Remove existing listener to avoid duplicates
  chrome.webRequest.onHeadersReceived.removeListener(onHeadersReceived);

  chrome.webRequest.onHeadersReceived.addListener(
    onHeadersReceived,
    { urls: ['<all_urls>'] },
    ['responseHeaders']
  );
}

function onHeadersReceived(details) {
  if (!enabled) return;
  if (details.type === 'main_frame') return; // Skip page navigations

  const url = details.url;

  // Skip already downloaded or ignored URLs
  if (downloadedUrls.has(url)) return;
  if (IGNORE_PATTERNS.some(p => p.test(url))) return;

  // Check 1: URL has video extension
  if (VIDEO_EXTENSIONS.test(url)) {
    downloadVideo(url, details.tabId);
    return;
  }

  // Check 2: Content-Type header indicates video
  if (details.responseHeaders) {
    const contentType = details.responseHeaders.find(
      h => h.name.toLowerCase() === 'content-type'
    );
    if (contentType && contentType.value) {
      const ct = contentType.value.toLowerCase();
      if (VIDEO_MIME_PATTERNS.some(mime => ct.includes(mime))) {
        downloadVideo(url, details.tabId);
        return;
      }
    }

    // Check 3: Large file with octet-stream might be video
    const contentLength = details.responseHeaders.find(
      h => h.name.toLowerCase() === 'content-length'
    );
    const contentDisposition = details.responseHeaders.find(
      h => h.name.toLowerCase() === 'content-disposition'
    );
    if (contentDisposition && contentDisposition.value) {
      const disp = contentDisposition.value.toLowerCase();
      if (VIDEO_EXTENSIONS.test(disp)) {
        downloadVideo(url, details.tabId);
        return;
      }
    }
  }

  // Check 4: URL matches known video hosting patterns
  if (VIDEO_HOST_PATTERNS.some(p => p.test(url))) {
    // Only download if it looks like an actual video stream/file
    if (url.includes('.mp4') || url.includes('/manifest') ||
        url.includes('master.m3u8') || url.includes('/video/')) {
      downloadVideo(url, details.tabId);
    }
  }
}

async function downloadVideo(url, tabId) {
  if (downloadedUrls.has(url)) return;
  downloadedUrls.add(url);
  stats.detected++;

  // Skip m3u8 playlists (streaming manifests, not actual files)
  if (url.includes('.m3u8') || url.includes('.mpd')) {
    console.log(`[VideoSaver] Skipping streaming manifest: ${url}`);
    return;
  }

  // Get page title for filename
  let pageTitle = 'video';
  try {
    if (tabId) {
      const tab = await chrome.tabs.get(tabId);
      pageTitle = tab.title || 'video';
    }
  } catch (e) {}

  const safeTitle = pageTitle
    .replace(/[<>:"/\\|?*]/g, '_')
    .replace(/\s+/g, ' ')
    .trim()
    .substring(0, 60);

  // Extract extension from URL
  const extMatch = url.match(/\.(mp4|webm|mkv|avi|mov|m4v|flv|wmv|mpg|mpeg)/i);
  const ext = extMatch ? extMatch[1].toLowerCase() : 'mp4';

  const timestamp = new Date().toISOString().slice(0, 10);
  const filename = `VideoSaver/${safeTitle}_${timestamp}.${ext}`;

  try {
    await chrome.downloads.download({
      url: url,
      filename: filename,
      saveAs: false
    });

    stats.downloaded++;
    stats.videos.push({
      title: safeTitle,
      url: url.substring(0, 100),
      time: new Date().toLocaleTimeString()
    });

    // Keep last 50 entries
    if (stats.videos.length > 50) stats.videos.shift();

    console.log(`[VideoSaver] Downloaded: ${filename}`);
  } catch (error) {
    stats.failed++;
    console.error(`[VideoSaver] Failed: ${error.message} — ${url}`);
  }
}

// Scan a tab for video elements in the DOM
async function scanTabForVideos(tabId) {
  try {
    const results = await chrome.scripting.executeScript({
      target: { tabId },
      func: findVideoSources
    });

    if (results && results[0] && results[0].result) {
      const urls = results[0].result;
      for (const url of urls) {
        if (!downloadedUrls.has(url)) {
          downloadVideo(url, tabId);
        }
      }
    }
  } catch (e) {
    console.error('[VideoSaver] Scan error:', e);
  }
}

// Injected into page to find video sources
function findVideoSources() {
  const urls = new Set();

  // Direct <video> elements
  document.querySelectorAll('video').forEach(v => {
    if (v.src) urls.add(v.src);
    if (v.currentSrc) urls.add(v.currentSrc);
  });

  // <source> elements inside <video>
  document.querySelectorAll('video source').forEach(s => {
    if (s.src) urls.add(s.src);
  });

  // Iframes that might contain video players
  document.querySelectorAll('iframe[src]').forEach(iframe => {
    const src = iframe.src;
    if (/panopto|kaltura|vimeo|youtube|brightcove|wistia/i.test(src)) {
      urls.add(src);
    }
  });

  // Links to video files
  document.querySelectorAll('a[href]').forEach(a => {
    if (/\.(mp4|webm|mkv|avi|mov|m4v)(\?|$)/i.test(a.href)) {
      urls.add(a.href);
    }
  });

  // Object/embed elements
  document.querySelectorAll('object[data], embed[src]').forEach(el => {
    const src = el.data || el.src;
    if (src && /video/i.test(src)) urls.add(src);
  });

  return [...urls];
}

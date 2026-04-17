// Content script for Web Note Extractor extension (Manifest V3)

// Extract main content intelligently
function extractMainContent() {
  const selectors = [
    'article',
    'main',
    '[role="main"]',
    '.main-content',
    '.content',
    '.post-content',
    '.entry-content',
    '#content',
    '.container'
  ];

  for (const selector of selectors) {
    const element = document.querySelector(selector);
    if (element && element.innerText.length > 100) {
      return element.innerText;
    }
  }
  return document.body.innerText;
}

// Scroll page to trigger lazy-loaded content
async function scrollToBottom() {
  return new Promise((resolve) => {
    let totalHeight = 0;
    const distance = 200;
    const timer = setInterval(() => {
      const scrollHeight = document.body.scrollHeight;
      window.scrollBy(0, distance);
      totalHeight += distance;
      if (totalHeight >= scrollHeight) {
        clearInterval(timer);
        // Brief pause for any final dynamic content
        setTimeout(resolve, 800);
      }
    }, 100);
  });
}

// Hide non-content elements for cleaner PDF printing
function prepareForPrint() {
  const elementsToHide = [
    'nav', 'header', 'footer', '.navbar', '.sidebar',
    '.navigation', '.menu', '[role="navigation"]',
    '.ads', '.advertisement', '.sidebar-widget',
    '.related-posts', '.comments-section'
  ];

  elementsToHide.forEach(selector => {
    try {
      document.querySelectorAll(selector).forEach(el => {
        el.style.display = 'none';
      });
    } catch (e) {
      // Ignore invalid selectors
    }
  });

  window.scrollTo(0, 0);
}

// Listen for messages from the popup
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === 'getPageContent') {
    sendResponse({
      title: document.title,
      text: document.body.innerText,
      html: document.documentElement.outerHTML,
      url: window.location.href
    });
  } else if (request.action === 'scrollAndExtract') {
    // Async handler — must return true to keep sendResponse alive
    scrollToBottom().then(() => {
      const text = extractMainContent();
      sendResponse({
        title: document.title,
        text: text,
        url: window.location.href
      });
    });
    return true; // keeps the message channel open for async response
  } else if (request.action === 'preparePrint') {
    prepareForPrint();
    sendResponse({ success: true });
  } else if (request.action === 'triggerPrint') {
    prepareForPrint();
    window.print();
    sendResponse({ success: true });
  }
});

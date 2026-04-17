// Display current page title on popup load
document.addEventListener('DOMContentLoaded', async () => {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  const pageTitle = document.getElementById('pageTitle');
  pageTitle.textContent = tab.title || 'Untitled Page';
});

// Helper to show status messages
function showStatus(message, type = 'info') {
  const statusEl = document.getElementById('status');
  statusEl.textContent = message;
  statusEl.className = `status ${type}`;

  if (type !== 'loading') {
    setTimeout(() => {
      statusEl.className = 'status';
    }, 4000);
  }
}

// Helper to sanitize filenames
function sanitizeFilename(text) {
  return text
    .replace(/[^a-z0-9]/gi, '_')
    .replace(/_+/g, '_')
    .replace(/^_|_$/g, '')
    .substring(0, 60);
}

// Send message to content script (with auto-injection fallback)
async function sendToContentScript(tabId, message) {
  try {
    return await chrome.tabs.sendMessage(tabId, message);
  } catch (e) {
    // Content script may not be injected yet — inject it and retry
    await chrome.scripting.executeScript({
      target: { tabId: tabId },
      files: ['content.js']
    });
    // Small delay to let the script initialize
    await new Promise(r => setTimeout(r, 100));
    return await chrome.tabs.sendMessage(tabId, message);
  }
}

// Extract text from current page
async function extractText() {
  showStatus('Scrolling and extracting text...', 'loading');

  try {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    const { title, text, url } = await sendToContentScript(tab.id, { action: 'scrollAndExtract' });

    const filename = sanitizeFilename(title) + '_' + new Date().toISOString().slice(0, 10);

    const fullContent = `URL: ${url}
Title: ${title}
Date: ${new Date().toLocaleString()}
${'─'.repeat(40)}

${text}`;

    const blob = new Blob([fullContent], { type: 'text/plain;charset=utf-8' });
    const downloadUrl = URL.createObjectURL(blob);

    await chrome.downloads.download({
      url: downloadUrl,
      filename: `WebNotes/${filename}.txt`,
      saveAs: false
    });

    showStatus('Text extracted and saved!', 'success');
  } catch (error) {
    console.error('Error:', error);
    showStatus('Error: ' + error.message, 'error');
  }
}

// Extract as PDF using browser print
async function extractPdf() {
  showStatus('Preparing page for PDF...', 'loading');

  try {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });

    // Scroll to load all content first
    await sendToContentScript(tab.id, { action: 'scrollAndExtract' });

    // Trigger print dialog via content script (user saves as PDF from there)
    await sendToContentScript(tab.id, { action: 'triggerPrint' });

    showStatus('Print dialog opened — choose "Save as PDF".', 'success');
  } catch (error) {
    console.error('Error:', error);
    showStatus('Error: ' + error.message, 'error');
  }
}

// Extract both text file and PDF
async function extractBoth() {
  showStatus('Extracting text and preparing PDF...', 'loading');

  try {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });

    const { title, text, url } = await sendToContentScript(tab.id, { action: 'scrollAndExtract' });
    const filename = sanitizeFilename(title) + '_' + new Date().toISOString().slice(0, 10);

    // Save text file
    const fullContent = `URL: ${url}
Title: ${title}
Date: ${new Date().toLocaleString()}
${'─'.repeat(40)}

${text}`;

    const blob = new Blob([fullContent], { type: 'text/plain;charset=utf-8' });
    const downloadUrl = URL.createObjectURL(blob);

    await chrome.downloads.download({
      url: downloadUrl,
      filename: `WebNotes/${filename}.txt`,
      saveAs: false
    });

    // Trigger print dialog for PDF
    await sendToContentScript(tab.id, { action: 'triggerPrint' });

    showStatus('Text saved! Print dialog opened for PDF.', 'success');
  } catch (error) {
    console.error('Error:', error);
    showStatus('Error: ' + error.message, 'error');
  }
}

// Event listeners
document.getElementById('extractText').addEventListener('click', extractText);
document.getElementById('extractPdf').addEventListener('click', extractPdf);
document.getElementById('extractBoth').addEventListener('click', extractBoth);

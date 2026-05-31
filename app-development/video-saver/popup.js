const toggleEl = document.getElementById('toggle');
const labelEl = document.getElementById('toggleLabel');

// Load current state
chrome.runtime.sendMessage({ action: 'getStatus' }, (response) => {
  if (response) {
    updateToggle(response.enabled);
    updateStats(response.stats);
  }
});

// Toggle on/off
toggleEl.addEventListener('click', () => {
  const newState = !toggleEl.classList.contains('on');
  chrome.runtime.sendMessage({ action: 'toggle', enabled: newState }, (response) => {
    updateToggle(response.enabled);
  });
});

function updateToggle(on) {
  toggleEl.classList.toggle('on', on);
  labelEl.textContent = on ? 'ON — Monitoring' : 'OFF';
}

function updateStats(stats) {
  document.getElementById('statDetected').textContent = stats.detected;
  document.getElementById('statDownloaded').textContent = stats.downloaded;
  document.getElementById('statFailed').textContent = stats.failed;

  const log = document.getElementById('videoLog');
  if (stats.videos && stats.videos.length > 0) {
    log.className = 'active';
    log.innerHTML = stats.videos.map(v =>
      `<div class="log-item"><span class="log-time">${v.time}</span> ${v.title}</div>`
    ).reverse().join('');
  }
}

// Scan current page
document.getElementById('btnScan').addEventListener('click', async () => {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  chrome.runtime.sendMessage({ action: 'scanPage', tabId: tab.id });

  const btn = document.getElementById('btnScan');
  btn.textContent = 'Scanning...';
  btn.disabled = true;

  setTimeout(() => {
    btn.textContent = 'Scan This Page for Videos';
    btn.disabled = false;
    // Refresh stats
    chrome.runtime.sendMessage({ action: 'getStatus' }, (response) => {
      if (response) updateStats(response.stats);
    });
  }, 3000);
});

// Clear history
document.getElementById('btnClear').addEventListener('click', () => {
  chrome.runtime.sendMessage({ action: 'clearStats' });
  document.getElementById('statDetected').textContent = '0';
  document.getElementById('statDownloaded').textContent = '0';
  document.getElementById('statFailed').textContent = '0';
  document.getElementById('videoLog').className = '';
  document.getElementById('videoLog').innerHTML = '';
});

// Auto-refresh stats while popup is open
setInterval(() => {
  chrome.runtime.sendMessage({ action: 'getStatus' }, (response) => {
    if (response) updateStats(response.stats);
  });
}, 2000);

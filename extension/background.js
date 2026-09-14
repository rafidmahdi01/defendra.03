// Background service worker: store events and optionally forward to local backend
const EVENTS_KEY = 'defendra_browser_events_v1';

async function saveEvent(evt) {
  try {
    const { storage } = chrome;
    const prev = (await storage.local.get(EVENTS_KEY))[EVENTS_KEY] || [];
    prev.unshift(evt);
    await storage.local.set({ [EVENTS_KEY]: prev.slice(0, 200) });
    // show notification
    chrome.notifications.create('', {
      type: 'basic',
      iconUrl: 'icon48.png',
      title: 'Browser Monitor — suspicious event',
      message: `${evt.reason} @ ${new Date(evt.time).toLocaleTimeString()}`,
    });

    // optionally forward to local backend if configured
    const cfg = (await chrome.storage.local.get('defendra_backend_url'))['defendra_backend_url'] || 'http://127.0.0.1:8000/api/logs';
    try {
      await fetch(cfg, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          device_id: null,
          category: 'browser-monitor',
          severity: 'info',
          source: 'browser_extension',
          message: `${evt.reason}: ${evt.snippet || evt.pattern || ''}`.slice(0, 2000),
          raw_payload: evt,
        }),
      });
    } catch (e) {
      // fail silently
    }
  } catch (e) {
    console.error(e);
  }
}

chrome.runtime.onMessage.addListener((msg, sender) => {
  if (msg && msg.type === 'suspicious-event' && msg.payload) {
    const evt = { ...msg.payload, url: msg.payload.url || (sender.tab && sender.tab.url) || '', time: msg.payload.time || Date.now() };
    saveEvent(evt);
  }
});

// Expose a simple RPC for popup to read events
chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (msg && msg.type === 'get-events') {
    chrome.storage.local.get(EVENTS_KEY, (data) => {
      sendResponse(data[EVENTS_KEY] || []);
    });
    return true;
  }
});

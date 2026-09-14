document.addEventListener('DOMContentLoaded', async () => {
  const backendInput = document.getElementById('backendUrl');
  const saveBtn = document.getElementById('saveUrl');
  const refreshBtn = document.getElementById('refresh');
  const eventsEl = document.getElementById('events');
  const screenshotBtn = document.getElementById('screenshot');
  const optionsBtn = document.getElementById('options');

  const cfg = await chrome.storage.local.get('defendra_backend_url');
  backendInput.value = cfg.defendra_backend_url || 'http://127.0.0.1:8000/api/logs';

  saveBtn.addEventListener('click', async () => {
    await chrome.storage.local.set({ defendra_backend_url: backendInput.value });
    alert('Saved');
  });

  refreshBtn.addEventListener('click', async () => {
    eventsEl.innerHTML = '<div class="small">Loading...</div>';
    chrome.runtime.sendMessage({ type: 'get-events' }, (events) => {
      renderEvents(events || []);
    });
  });

  screenshotBtn.addEventListener('click', async () => {
    try {
      // user gesture required; this will ask the user to pick a screen/window/tab
      const stream = await navigator.mediaDevices.getDisplayMedia({ video: true });
      const track = stream.getVideoTracks()[0];
      const imageCapture = new ImageCapture(track);
      const bitmap = await imageCapture.grabFrame();
      // draw to canvas and send to backend as a data URL (optional)
      const canvas = document.createElement('canvas');
      canvas.width = bitmap.width;
      canvas.height = bitmap.height;
      const ctx = canvas.getContext('2d');
      ctx.drawImage(bitmap, 0, 0);
      track.stop();
      const dataUrl = canvas.toDataURL('image/png');
      const url = (await chrome.storage.local.get('defendra_backend_url')).defendra_backend_url || 'http://127.0.0.1:8000/api/logs';
      await fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ category: 'browser-screenshot', message: 'user-screenshot', raw_payload: { image: dataUrl.slice(0, 2000) } }) });
      alert('Screenshot sent (truncated for demo).');
    } catch (e) {
      alert('Screenshot cancelled or failed: ' + e.message);
    }
  });

  optionsBtn.addEventListener('click', () => {
    chrome.runtime.openOptionsPage();
  });

  function renderEvents(events) {
    if (!events || events.length === 0) {
      eventsEl.innerHTML = '<div class="no-events"><div class="no-events-icon">✓</div><div>No suspicious events detected</div></div>';
      return;
    }
    eventsEl.innerHTML = '';
    for (const e of events.slice(0, 200)) {
      const d = document.createElement('div');
      d.className = 'event';
      d.innerHTML = `
        <div class="event-reason">${e.reason}</div>
        <div class="event-time">⏰ ${new Date(e.time).toLocaleTimeString()}</div>
        ${e.url ? `<div class="event-url">📍 ${e.url}</div>` : ''}
        ${(e.snippet || e.pattern) ? `<div class="event-snippet">${(e.snippet || e.pattern || '').slice(0, 200)}</div>` : ''}
      `;
      eventsEl.appendChild(d);
    }
  }

  // initial refresh
  refreshBtn.click();
});

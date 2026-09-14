Defendra Browser Monitor (Demo)
================================

This is a minimal browser extension demo that detects suspicious page overlays, dynamically added password fields, and suspicious text patterns. It reports events to the extension background script which stores them locally and optionally forwards to a local Defendra backend at `http://127.0.0.1:8000/api/logs`.

Important: This is a demo. It does NOT capture your screen unless you explicitly press "Capture screen" in the popup and consent to sharing a display. Only use this on test pages and local machines.

Installation (Chrome/Edge)
1. Open `chrome://extensions` (or `edge://extensions`).
2. Enable "Developer mode".
3. Click "Load unpacked" and select this `extension/` folder.
4. Click the extension icon to open the popup and set the backend URL if different.

Testing
1. Open `extension/test_page.html` in the browser (File > Open File or serve it over `http://localhost`).
2. Click the "Insert large overlay" button — the extension should detect a large overlay and create an event.
3. Click the extension icon (popup) and press "Refresh events" — the event should be visible.
4. Optionally press "Capture screen" to manually capture your display; you'll be asked to share a screen/tab and the popup will send a truncated data URL to the backend.

Server integration
- By default the popup will POST to `http://127.0.0.1:8000/api/logs`. Ensure your backend accepts the payload or change the URL in the popup.

Security & privacy
- The extension intentionally avoids taking screenshots without explicit user action.
- Do not install this extension in production or on shared machines — it's a demo for testing heuristics.

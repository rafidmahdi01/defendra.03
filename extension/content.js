// Content script: heuristics for suspicious UI behaviour
(() => {
  const THRESH_DOM_CHURN = 150; // mutations/sec that look suspicious
  let mutationsInWindow = 0;

  const report = (payload) => {
    try {
      chrome.runtime.sendMessage({ type: 'suspicious-event', payload });
    } catch (e) {
      // no-op
    }
  };

  // Heuristic: large overlay covering most of viewport
  function isLargeOverlay(el) {
    try {
      const rect = el.getBoundingClientRect();
      const area = rect.width * rect.height;
      const vw = window.innerWidth;
      const vh = window.innerHeight;
      if (area <= 0) return false;
      if (rect.width < 50 || rect.height < 50) return false;
      const coverRatio = (area / (vw * vh));
      const style = window.getComputedStyle(el);
      const z = parseInt(style.zIndex || '0') || 0;
      return coverRatio > 0.6 && z > 0;
    } catch (e) { return false; }
  }

  // Heuristic: suspicious text patterns
  const SUSPICIOUS_PATTERNS = [/update (your )?browser/i, /install (an )?extension/i, /click allow to continue/i, /you must enable/i, /verify your payment/i];

  const obs = new MutationObserver((list) => {
    mutationsInWindow += list.length;
    for (const m of list) {
      for (const n of m.addedNodes) {
        if (!(n instanceof HTMLElement)) continue;
        // password inputs added dynamically
        if (n.querySelector && n.querySelector('input[type=password]')) {
          report({ reason: 'password-field-added', snippet: n.outerHTML.slice(0, 800), url: location.href, time: Date.now() });
        }
        // large overlays
        if (isLargeOverlay(n)) {
          report({ reason: 'large-overlay', snippet: n.outerHTML.slice(0, 800), url: location.href, time: Date.now() });
        }
        // suspicious text hints
        const text = (n.textContent || '').slice(0, 800);
        for (const re of SUSPICIOUS_PATTERNS) {
          if (re.test(text)) {
            report({ reason: 'suspicious-text', pattern: re.toString(), snippet: text, url: location.href, time: Date.now() });
            break;
          }
        }
      }
    }
  });

  // measure churn
  setInterval(() => {
    if (mutationsInWindow > THRESH_DOM_CHURN) {
      report({ reason: 'dom-churn', count: mutationsInWindow, url: location.href, time: Date.now() });
    }
    mutationsInWindow = 0;
  }, 1000);

  obs.observe(document, { childList: true, subtree: true });

  // detect initial big overlays or existing password fields
  try {
    if (document.querySelector('input[type=password]')) {
      report({ reason: 'password-field-present', url: location.href, time: Date.now() });
    }
    // scan for overlays
    const all = Array.from(document.body ? document.body.querySelectorAll('*') : []);
    for (const el of all.slice(0, 200)) {
      if (isLargeOverlay(el)) {
        report({ reason: 'large-overlay-present', snippet: el.outerHTML.slice(0, 800), url: location.href, time: Date.now() });
        break;
      }
    }
  } catch (e) {}

  // allow page to send a test event
  window.addEventListener('defendra_browser_monitor_test', (ev) => {
    report({ reason: 'test-event', detail: ev.detail, url: location.href, time: Date.now() });
  });
})();

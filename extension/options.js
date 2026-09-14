document.addEventListener('DOMContentLoaded', async () => {
  const backendUrlInput = document.getElementById('backendUrl');
  const saveBackendBtn = document.getElementById('saveBackend');
  const backendStatus = document.getElementById('backendStatus');

  const enableLogDetection = document.getElementById('enableLogDetection');
  const enableNotifications = document.getElementById('enableNotifications');
  const enableBackendSync = document.getElementById('enableBackendSync');
  const enableScreenCapture = document.getElementById('enableScreenCapture');
  const savePermissionsBtn = document.getElementById('savePermissions');
  const permStatus = document.getElementById('permStatus');

  const domChurnThreshold = document.getElementById('domChurnThreshold');
  const overlayCoverageThreshold = document.getElementById('overlayCoverageThreshold');
  const saveHeuristicsBtn = document.getElementById('saveHeuristics');
  const heuristicStatus = document.getElementById('heuristicStatus');

  const exportEventsBtn = document.getElementById('exportEvents');
  const clearEventsBtn = document.getElementById('clearEvents');
  const dataStatus = document.getElementById('dataStatus');

  // Load backend URL
  const cfg = await chrome.storage.local.get('defendra_backend_url');
  backendUrlInput.value = cfg.defendra_backend_url || 'http://127.0.0.1:8000/api/logs';

  // Load permissions
  const perms = await chrome.storage.local.get('defendra_permissions');
  const defaultPerms = {
    enableLogDetection: true,
    enableNotifications: true,
    enableBackendSync: true,
    enableScreenCapture: true,
  };
  const currentPerms = perms.defendra_permissions || defaultPerms;
  enableLogDetection.checked = currentPerms.enableLogDetection !== false;
  enableNotifications.checked = currentPerms.enableNotifications !== false;
  enableBackendSync.checked = currentPerms.enableBackendSync !== false;
  enableScreenCapture.checked = currentPerms.enableScreenCapture !== false;

  // Load heuristics
  const heur = await chrome.storage.local.get('defendra_heuristics');
  const defaultHeur = { domChurnThreshold: 150, overlayCoverageThreshold: 0.6 };
  const currentHeur = heur.defendra_heuristics || defaultHeur;
  domChurnThreshold.value = currentHeur.domChurnThreshold;
  overlayCoverageThreshold.value = currentHeur.overlayCoverageThreshold;

  // Save backend URL
  saveBackendBtn.addEventListener('click', async () => {
    await chrome.storage.local.set({ defendra_backend_url: backendUrlInput.value });
    showStatus(backendStatus, '✓ Backend URL saved');
  });

  // Save permissions
  savePermissionsBtn.addEventListener('click', async () => {
    const newPerms = {
      enableLogDetection: enableLogDetection.checked,
      enableNotifications: enableNotifications.checked,
      enableBackendSync: enableBackendSync.checked,
      enableScreenCapture: enableScreenCapture.checked,
    };
    await chrome.storage.local.set({ defendra_permissions: newPerms });
    showStatus(permStatus, '✓ Permissions saved');
  });

  // Save heuristics
  saveHeuristicsBtn.addEventListener('click', async () => {
    const threshold = parseFloat(domChurnThreshold.value) || 150;
    const coverage = parseFloat(overlayCoverageThreshold.value) || 0.6;
    
    if (coverage < 0 || coverage > 1) {
      showStatus(heuristicStatus, '✗ Coverage must be between 0 and 1', true);
      return;
    }
    
    const newHeur = {
      domChurnThreshold: threshold,
      overlayCoverageThreshold: coverage,
    };
    await chrome.storage.local.set({ defendra_heuristics: newHeur });
    showStatus(heuristicStatus, '✓ Heuristics saved');
  });

  // Export events
  exportEventsBtn.addEventListener('click', async () => {
    const data = await chrome.storage.local.get('defendra_browser_events_v1');
    const events = data['defendra_browser_events_v1'] || [];
    const json = JSON.stringify(events, null, 2);
    const blob = new Blob([json], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `defendra-events-${Date.now()}.json`;
    a.click();
    URL.revokeObjectURL(url);
    showStatus(dataStatus, '✓ Events exported');
  });

  // Clear events
  clearEventsBtn.addEventListener('click', async () => {
    if (confirm('Are you sure you want to clear all events? This cannot be undone.')) {
      await chrome.storage.local.set({ defendra_browser_events_v1: [] });
      showStatus(dataStatus, '✓ All events cleared');
    }
  });

  function showStatus(element, message, isError = false) {
    element.textContent = message;
    element.style.display = 'block';
    if (isError) {
      element.classList.remove('status-success');
      element.classList.add('status-error');
    } else {
      element.classList.remove('status-error');
      element.classList.add('status-success');
    }
    setTimeout(() => {
      element.style.display = 'none';
    }, 3000);
  }
});

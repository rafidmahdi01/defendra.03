const QUEUE_KEY = "crps_offline_queue";

export function getQueuedLogs() {
  return JSON.parse(localStorage.getItem(QUEUE_KEY) || "[]");
}

export function queueLog(log) {
  const queue = getQueuedLogs();
  queue.push({ ...log, queued_at: new Date().toISOString() });
  localStorage.setItem(QUEUE_KEY, JSON.stringify(queue));
}

export function clearQueuedLogs() {
  localStorage.removeItem(QUEUE_KEY);
}

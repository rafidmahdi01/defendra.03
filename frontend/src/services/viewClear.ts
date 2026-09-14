/** Persist “cleared” UI state across navigation within the same browser tab. */

const PREFIX = "defendra_view_";

export function isViewCleared(key: string): boolean {
  return sessionStorage.getItem(`${PREFIX}${key}`) === "1";
}

export function setViewCleared(key: string, cleared: boolean): void {
  if (cleared) sessionStorage.setItem(`${PREFIX}${key}`, "1");
  else sessionStorage.removeItem(`${PREFIX}${key}`);
}

export function getDismissedIds(key: string): Set<string> {
  try {
    const raw = sessionStorage.getItem(`${PREFIX}${key}_ids`);
    if (!raw) return new Set();
    const parsed = JSON.parse(raw) as unknown;
    return new Set(Array.isArray(parsed) ? parsed.map(String) : []);
  } catch {
    return new Set();
  }
}

export function dismissIds(key: string, ids: Array<string | number>): void {
  const set = getDismissedIds(key);
  ids.forEach((id) => set.add(String(id)));
  sessionStorage.setItem(`${PREFIX}${key}_ids`, JSON.stringify([...set]));
}

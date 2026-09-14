let cached: { value: string; at: number } | null = null;
const TTL_MS = 30 * 60 * 1000;

function timezoneFallback(): string {
  try {
    return Intl.DateTimeFormat().resolvedOptions().timeZone.replace(/_/g, " ");
  } catch {
    return "Unknown location";
  }
}

/** Resolve a readable location label for this browser/workstation. */
export async function resolveDeviceLocation(force = false): Promise<string> {
  if (!force && cached && Date.now() - cached.at < TTL_MS) {
    return cached.value;
  }

  try {
    const res = await fetch(
      "http://ip-api.com/json/?fields=status,city,regionName,country,query",
      { signal: AbortSignal.timeout(6000) },
    );
    if (res.ok) {
      const data = (await res.json()) as {
        status?: string;
        city?: string;
        regionName?: string;
        country?: string;
        query?: string;
      };
      if (data.status === "success") {
        const parts = [data.city, data.regionName, data.country].filter(Boolean);
        if (parts.length) {
          const label = parts.join(", ");
          const value = data.query ? `${label} (${data.query})` : label;
          cached = { value, at: Date.now() };
          return value;
        }
      }
    }
  } catch {
    /* network / mixed content — fall back below */
  }

  const fallback = timezoneFallback();
  cached = { value: fallback, at: Date.now() };
  return fallback;
}

export function formatDeviceLocation(
  location?: string | null,
  ipAddress?: string | null,
): string {
  const value = (location || "").trim();
  if (value) return value;

  const ip = (ipAddress || "").trim();
  if (ip && ip !== "127.0.0.1") {
    return `Local network · ${ip}`;
  }
  return "Location unavailable";
}

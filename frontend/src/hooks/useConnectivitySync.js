import { useEffect, useState } from "react";

import { api } from "../services/api";
import { clearQueuedLogs, getQueuedLogs } from "../services/offlineQueue";

export function useConnectivitySync(deviceId) {
  const [online, setOnline] = useState(navigator.onLine);
  const [pending, setPending] = useState(getQueuedLogs().length);

  useEffect(() => {
    const sync = async () => {
      setOnline(navigator.onLine);
      const queued = getQueuedLogs();
      setPending(queued.length);
      if (!navigator.onLine || !queued.length || !deviceId) return;
      await api.post("/sync/offline-logs", { device_id: deviceId, logs: queued });
      clearQueuedLogs();
      setPending(0);
    };
    window.addEventListener("online", sync);
    window.addEventListener("offline", sync);
    sync();
    return () => {
      window.removeEventListener("online", sync);
      window.removeEventListener("offline", sync);
    };
  }, [deviceId]);

  return { online, pending };
}

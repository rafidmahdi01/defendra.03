import { useEffect, useState } from "react";

import { useServiceConnected } from "@/hooks/useServiceConnected";
import { api, getWorkstationDeviceId, isWorkstationLinked } from "@/services/api";
import { resolveDeviceLocation } from "@/services/deviceLocation";

/** Sends CPU/RAM from the Electron main process to the API so fleet views stay current. */
export function WorkstationHeartbeat() {
  const { connected } = useServiceConnected();
  const [linked, setLinked] = useState(() => isWorkstationLinked());

  useEffect(() => {
    const onLink = () => setLinked(true);
    const onUnlink = () => setLinked(false);
    window.addEventListener("crps-workstation-linked", onLink);
    window.addEventListener("crps-workstation-unlinked", onUnlink);
    return () => {
      window.removeEventListener("crps-workstation-linked", onLink);
      window.removeEventListener("crps-workstation-unlinked", onUnlink);
    };
  }, []);

  useEffect(() => {
    if (!window.crpsDesktop?.getSystemMetrics) return;
    if (!linked) return;
    const deviceId = getWorkstationDeviceId();
    if (!deviceId) return;

    let cancelled = false;

    const tick = async () => {
      if (cancelled || !connected || !isWorkstationLinked()) return;
      const id = getWorkstationDeviceId();
      if (!id) return;
      try {
        const m = await window.crpsDesktop!.getSystemMetrics();
        const info = window.crpsDesktop?.getMachineInfo
          ? await window.crpsDesktop.getMachineInfo()
          : null;
        const location = await resolveDeviceLocation();
        await api.post(`/devices/${id}/heartbeat`, {
          status: "online",
          cpu_usage: m.cpu_usage,
          ram_usage: m.ram_usage,
          ip_address: info?.ip_address,
          location,
        });
      } catch {
        /* avoid console noise when offline */
      }
    };

    tick();
    const interval = setInterval(tick, 12_000);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, [connected, linked]);

  return null;
}

import { useEffect, useState, type ReactNode } from "react";
import { useNavigate } from "react-router-dom";
import { Cpu, Link2, Loader2, LogOut, WifiOff } from "lucide-react";

import { useServiceConnected } from "@/hooks/useServiceConnected";
import {
  api,
  clearWorkstationLink,
  isElectronApp,
  isWorkstationLinked,
  setWorkstationLinked,
} from "@/services/api";
import { resolveDeviceLocation } from "@/services/deviceLocation";

export function WorkstationLinkGate({ children }: { children: ReactNode }) {
  const navigate = useNavigate();
  const { connected, checking } = useServiceConnected();
  const [linked, setLinked] = useState(() => isWorkstationLinked());
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const electron = isElectronApp();

  useEffect(() => {
    const onLink = () => {
      setLinked(true);
      setOpen(false);
    };
    const onUnlink = () => {
      setLinked(false);
      setOpen(true);
    };
    const onOpen = () => setOpen(true);
    window.addEventListener("crps-workstation-linked", onLink);
    window.addEventListener("crps-workstation-unlinked", onUnlink);
    window.addEventListener("crps-open-workstation-modal", onOpen);
    return () => {
      window.removeEventListener("crps-workstation-linked", onLink);
      window.removeEventListener("crps-workstation-unlinked", onUnlink);
      window.removeEventListener("crps-open-workstation-modal", onOpen);
    };
  }, []);

  useEffect(() => {
    if (!electron || linked) return;
    setOpen(true);
  }, [electron, linked]);

  const handleConnect = async () => {
    if (!connected || !window.crpsDesktop?.getMachineInfo) return;
    setErr(null);
    setBusy(true);
    try {
      const info = await window.crpsDesktop.getMachineInfo();
      let agentVer = "defendra-desktop";
      try {
        const v = await window.crpsDesktop.getVersion();
        if (v) agentVer = `electron-${String(v)}`;
      } catch {
        /* ignore */
      }
      const location = await resolveDeviceLocation();
      const { data } = await api.post<{ id: string }>("/devices/workstation/link", {
        hostname: info.hostname,
        platform: info.platform,
        os_name: `${info.platform} (${info.arch})`,
        agent_version: agentVer,
        ip_address: info.ip_address,
        location,
      });
      setWorkstationLinked(data.id);
      setLinked(true);
      setOpen(false);
    } catch (e: unknown) {
      const msg =
        e && typeof e === "object" && "message" in e
          ? String((e as { message: string }).message)
          : "Could not link this computer.";
      setErr(msg);
    } finally {
      setBusy(false);
    }
  };

  const handleLogout = () => {
    localStorage.removeItem("crps_token");
    localStorage.removeItem("crps_user");
    clearWorkstationLink();
    navigate("/login");
  };

  if (!electron) return children;

  return (
    <>
      {children}
      {open && !linked && (
        <div
          className="fixed inset-0 z-[100] flex items-center justify-center bg-[#050816]/92 px-4 backdrop-blur-md"
          role="dialog"
          aria-modal="true"
          aria-labelledby="ws-link-title"
        >
          <div className="glass relative max-w-lg rounded-3xl border border-[var(--mint)]/25 p-8 shadow-2xl">
            <div className="mb-6 flex items-center gap-3">
              <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-[var(--mint)]/15 ring-1 ring-[var(--mint)]/35">
                <Cpu className="h-6 w-6 text-[var(--mint)]" />
              </div>
              <div>
                <h2 id="ws-link-title" className="text-lg font-semibold tracking-tight">
                  Connect this computer
                </h2>
                <p className="text-[11px] text-muted-foreground">
                  Required for the Defendra desktop app
                </p>
              </div>
            </div>

            <p className="text-sm leading-relaxed text-muted-foreground">
              Link registers this PC with your protection server. Until you connect,{" "}
              <span className="font-medium text-foreground">
                this application will not load fleet data or use the API
              </span>
              — so from Defendra&apos;s perspective the workstation is offline. Your browser and other
              apps still use the internet normally; turning off internet for the entire PC is not done by
              this app and would need Windows admin or MDM policies outside Defendra.
            </p>

            {!connected && !checking && (
              <div className="mt-4 flex items-center gap-2 rounded-xl border border-[var(--danger)]/30 bg-[var(--danger)]/10 px-3 py-2 text-[11px] text-[var(--danger)]">
                <WifiOff className="h-3.5 w-3.5 shrink-0" />
                Start the backend and ensure the server is reachable, then try again.
              </div>
            )}

            {err && <p className="mt-3 text-xs text-[var(--danger)]">{err}</p>}

            <div className="mt-6 flex flex-wrap items-center gap-3">
              <button
                type="button"
                disabled={!connected || busy}
                onClick={handleConnect}
                className="flex min-w-[200px] flex-1 items-center justify-center gap-2 rounded-xl bg-gradient-cyber px-5 py-3 text-sm font-semibold text-black transition hover:brightness-110 disabled:cursor-not-allowed disabled:opacity-40"
              >
                {busy ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Link2 className="h-4 w-4" />
                )}
                Connect this PC
              </button>
            </div>

            <div className="mt-6 flex justify-end border-t border-white/10 pt-4">
              <button
                type="button"
                onClick={handleLogout}
                className="flex items-center gap-2 text-[11px] text-muted-foreground transition hover:text-foreground"
              >
                <LogOut className="h-3.5 w-3.5" />
                Sign out
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

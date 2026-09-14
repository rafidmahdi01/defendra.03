import { useState, useEffect, useCallback } from "react";
import {
  Usb,
  Ban,
  ShieldOff,
  ScrollText,
  ShieldAlert,
  CheckCircle2,
  FileCode2,
  EyeOff,
  Zap,
  ShieldX,
  HardDrive,
  Trash2,
  RefreshCw,
} from "lucide-react";
import { GlassCard } from "@/components/defendra/Card";
import { useServiceConnected } from "@/hooks/useServiceConnected";
import { api } from "@/services/api";
import { dismissIds, getDismissedIds } from "@/services/viewClear";

type RiskStatus = "Safe" | "Suspicious" | "Malicious";
type AccessStatus = "Allow" | "Block";

type UsbDevice = {
  id: string;
  alertId: string;
  deviceName: string;
  serialNo: string;
  fileCount: number;
  riskStatus: RiskStatus;
  access: AccessStatus;
  scan: {
    executableFiles: number;
    hiddenFiles: number;
    autorunFile: boolean;
    scanResult: string;
    actionTaken: string;
  };
};


function riskColor(risk: RiskStatus) {
  if (risk === "Safe")      return "var(--success)";
  if (risk === "Suspicious") return "var(--warning)";
  return "var(--danger)";
}

function accessColor(access: AccessStatus) {
  return access === "Allow" ? "var(--success)" : "var(--danger)";
}

function alertToUsbDevice(alert: Record<string, unknown>, index: number): UsbDevice {
  const description = String(alert.description ?? "");
  const ruleN = String(alert.rule_name ?? "");
  const isThreat = ruleN === "usb_threat" || String(alert.severity) === "critical";
  const drive = description.match(/USB\s+([A-Z]:\\)/i)?.[1] ?? "Unknown";
  const quarantined = description.match(/Quarantined (\d+) files/)?.[1];
  const fileCount = quarantined ? parseInt(quarantined) : 0;
  const alertId = String(alert.id ?? index);

  return {
    id: alertId,
    alertId,
    deviceName: `USB Drive (${drive})`,
    serialNo: String(alert.id ?? "").slice(0, 8).toUpperCase(),
    fileCount,
    riskStatus: isThreat ? "Malicious" : "Safe",
    access: isThreat ? "Block" : "Allow",
    scan: {
      executableFiles: isThreat ? fileCount : 0,
      hiddenFiles: 0,
      autorunFile: description.toLowerCase().includes("autorun"),
      scanResult: isThreat ? "Threats Found" : "Clean",
      actionTaken: isThreat ? "Quarantined" : "Allowed",
    },
  };
}

function logToUsbDevice(log: Record<string, unknown>, index: number): UsbDevice {
  const message = String(log.message ?? log.message ?? "");
  const drive = message.match(/USB\s+([A-Z]:\\)/i)?.[1] ?? "Unknown";
  const nameMatch = message.match(/USB peripheral connected:\s*(.+)$/i) || message.match(/usb peripheral connected:\s*(.+)$/i);
  const deviceName = nameMatch ? String(nameMatch[1]) : `USB Drive (${drive})`;
  const alertId = String(log.id ?? `log-${index}`);
  return {
    id: alertId,
    alertId,
    deviceName,
    serialNo: String((log.id ?? "").toString().slice(0, 8)).toUpperCase(),
    fileCount: 0,
    riskStatus: "Safe",
    access: "Allow",
    scan: {
      executableFiles: 0,
      hiddenFiles: 0,
      autorunFile: false,
      scanResult: "Clean",
      actionTaken: "Allowed",
    },
  };
}

const USB_VIEW_KEY = "usb";

export default function UsbPage() {
  const { connected } = useServiceConnected();
  const [devices, setDevices] = useState<UsbDevice[]>([]);
  const [selected, setSelected] = useState<UsbDevice | null>(null);
  const [loading, setLoading] = useState(false);

  const fetchUsbAlerts = useCallback(async () => {
    if (!connected) return;
    setLoading(true);
    try {
      const [alertsRes, logsRes] = await Promise.all([
        api.get<Record<string, unknown>[]>('/alerts?limit=200'),
        api.get<Record<string, unknown>[]>('/logs?limit=200'),
      ]);
      const alerts: Record<string, unknown>[] = alertsRes.data ?? [];
      const logs: Record<string, unknown>[] = logsRes.data ?? [];
      const dismissed = getDismissedIds(USB_VIEW_KEY);

      // Alerts that are USB-related (rule_name starts with usb)
      const usbAlerts = alerts.filter((a) => {
        const rn = String(a.rule_name ?? "").toLowerCase();
        return rn.startsWith("usb") && !dismissed.has(String(a.id ?? ""));
      });

      // Logs that are explicit USB peripheral connect messages (category=usb and message indicates peripheral)
      const usbLogs = (logs || []).filter((l) => {
        try {
          const category = String(l.category ?? "").toLowerCase();
          const msg = String(l.message ?? "").toLowerCase();
          const isUsbCat = category === "usb" || category === "agent" || category === "device";
          const containsPeripheral = msg.includes("usb peripheral connected") || msg.includes("hid-compliant mouse") || msg.includes("usb input device");
          return isUsbCat && containsPeripheral && !dismissed.has(String(l.id ?? ""));
        } catch {
          return false;
        }
      });

      // Map alerts and logs to unified device rows, then dedupe by alertId
      const mappedAlerts = usbAlerts.map((a, i) => alertToUsbDevice(a, i));
      const mappedLogs = usbLogs.map((l, i) => logToUsbDevice(l, i));

      const all = [...mappedAlerts, ...mappedLogs];
      const seen = new Set<string>();
      const deduped: UsbDevice[] = [];
      for (const item of all) {
        const key = (item.deviceName || "") + "|" + (item.serialNo || "") + "|" + (item.fileCount || 0);
        if (seen.has(key)) continue;
        seen.add(key);
        deduped.push(item);
      }
      setDevices(deduped);
    } catch {
      // silently ignore
    } finally {
      setLoading(false);
    }
  }, [connected]);

  useEffect(() => {
    fetchUsbAlerts();
    const id = setInterval(fetchUsbAlerts, 15_000);
    return () => clearInterval(id);
  }, [fetchUsbAlerts]);

  const usbPresent = devices.length > 0;
  const canOperateUsb = connected && usbPresent;

  const blocked    = devices.filter((d) => d.access === "Block").length;
  const allowed    = devices.filter((d) => d.access === "Allow").length;
  const suspicious = devices.filter((d) => d.riskStatus !== "Safe").length;

  const rowCls = (active: boolean) =>
    `border-t border-white/5 transition ${canOperateUsb ? "cursor-pointer hover:bg-white/[0.04]" : "cursor-default opacity-70"} ${
      active ? "bg-white/[0.06] ring-inset ring-1 ring-[var(--mint)]/20" : ""
    }`;

  return (
    <div className="space-y-4">
      {/* Header */}
      <header className="flex flex-wrap items-end justify-between gap-3 px-1">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">USB Security</h1>
          <p className="text-xs text-muted-foreground">
            Device control · removable media monitoring
          </p>
        </div>
        <div className="flex gap-2">
          <button
            type="button"
            onClick={fetchUsbAlerts}
            disabled={loading || !connected}
            className="flex items-center gap-1.5 rounded-xl border border-white/10 bg-white/5 px-3 py-2 text-xs font-medium text-muted-foreground transition hover:bg-white/10 disabled:cursor-not-allowed disabled:opacity-40"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`} /> Refresh
          </button>
          <button
            type="button"
            disabled={!connected || devices.length === 0}
            onClick={() => {
              if (!connected || devices.length === 0) return;
              
              const confirmed = window.confirm(
                `Are you sure you want to clear all ${devices.length} USB device alert${devices.length !== 1 ? 's' : ''}? This will dismiss them from view.`
              );
              
              if (!confirmed) return;
              
              dismissIds(USB_VIEW_KEY, devices.map((d) => d.alertId));
              setDevices([]);
              setSelected(null);
            }}
            className="flex items-center gap-1.5 rounded-xl border border-[var(--danger)]/30 bg-[var(--danger)]/10 px-3 py-2 text-xs font-medium text-[var(--danger)] transition hover:bg-[var(--danger)]/20 disabled:cursor-not-allowed disabled:opacity-40"
          >
            <Trash2 className="h-3.5 w-3.5" /> Clear All
          </button>
        </div>
      </header>

      {/* Stat cards */}
      <div className="grid gap-4 sm:grid-cols-3">
        <StatCard icon={<CheckCircle2 className="h-5 w-5" />} label="Allowed"     value={allowed}    color="var(--success)" />
        <StatCard icon={<Ban className="h-5 w-5" />}          label="Blocked"     value={blocked}    color="var(--danger)"  />
        <StatCard icon={<ShieldOff className="h-5 w-5" />}    label="Suspicious"  value={suspicious} color="var(--warning)" />
      </div>

      {/* Connected External Devices banner */}
      <div className="glass rounded-2xl px-5 py-3 flex items-center gap-3">
        <Usb className="h-5 w-5 text-[var(--cyan)]" />
        <div>
          <p className="text-sm font-semibold">Connected External Devices</p>
          <p className="text-[11px] text-muted-foreground">{devices.length} USB device{devices.length !== 1 ? "s" : ""} currently detected</p>
        </div>
        <span
          className={`ml-auto flex items-center gap-1.5 rounded-lg px-3 py-1 text-[11px] font-medium ring-1 ${
            canOperateUsb
              ? "bg-[var(--cyan)]/10 text-[var(--cyan)] ring-[var(--cyan)]/30"
              : "bg-white/5 text-muted-foreground ring-white/10"
          }`}
        >
          {canOperateUsb ? (
            <>
              <span className="h-1.5 w-1.5 rounded-full bg-[var(--cyan)] animate-pulse" />
              Live monitoring
            </>
          ) : !connected ? (
            <>Server offline</>
          ) : (
            <>No USB — standby</>
          )}
        </span>
      </div>

      {/* Main: USB Activity table + Scan Details */}
      <div className="grid gap-4 lg:grid-cols-[1fr_320px]">

        {/* USB Activity table */}
        <GlassCard
          title="USB Activity"
          subtitle={`${devices.length} devices detected`}
          icon={<HardDrive className="h-4 w-4 text-[var(--cyan)]" />}
        >
          <div className="overflow-hidden rounded-xl ring-1 ring-white/5">
            <table className="w-full text-left text-xs">
              <thead className="bg-white/5 text-[10px] uppercase tracking-wider text-muted-foreground">
                <tr>
                  <Th>Device Name</Th>
                  <Th>Serial No.</Th>
                  <Th>File Count</Th>
                  <Th>Risk Status</Th>
                  <Th>Access</Th>
                  <Th>Action</Th>
                </tr>
              </thead>
              <tbody>
                {devices.length === 0 && (
                  <tr>
                    <td colSpan={6} className="px-3 py-8 text-center text-muted-foreground text-xs">
                      No USB activity recorded.
                    </td>
                  </tr>
                )}
                {devices.map((d) => (
                  <tr
                    key={d.id}
                    onClick={() => canOperateUsb && setSelected(d)}
                    className={rowCls(selected?.id === d.id)}
                  >
                    <Td>
                      <div className="flex items-center gap-2 font-medium">
                        <Usb className="h-3.5 w-3.5 shrink-0 text-[var(--cyan)]" />
                        {d.deviceName}
                      </div>
                    </Td>
                    <Td className="tabular-nums text-muted-foreground">{d.serialNo}</Td>
                    <Td className="tabular-nums">{d.fileCount}</Td>
                    <Td><RiskPill risk={d.riskStatus} /></Td>
                    <Td>
                      <span
                        className="inline-flex items-center gap-1 rounded-md px-2 py-0.5 text-[10px] font-medium ring-1"
                        style={{
                          color: accessColor(d.access),
                          background: `${accessColor(d.access)}1f`,
                          borderColor: `${accessColor(d.access)}55`,
                        }}
                      >
                        {d.access}
                      </span>
                    </Td>
                    <Td>
                      <div className="flex gap-1.5">
                        <button
                          type="button"
                          disabled={!canOperateUsb}
                          className="flex items-center gap-1 rounded-lg px-2.5 py-1 text-[10px] font-medium ring-1 transition hover:brightness-125 disabled:cursor-not-allowed disabled:opacity-40"
                          style={{ color: "var(--cyan)", background: "oklch(0.86 0.2 165 / 0.1)", borderColor: "oklch(0.86 0.2 165 / 0.3)" }}
                        >
                          <ScrollText className="h-3 w-3" /> Open Log
                        </button>
                        {d.riskStatus !== "Safe" && (
                          <button
                            type="button"
                            disabled={!canOperateUsb}
                            className="flex items-center gap-1 rounded-lg px-2.5 py-1 text-[10px] font-medium ring-1 transition hover:brightness-125 disabled:cursor-not-allowed disabled:opacity-40"
                            style={{ color: "var(--danger)", background: "oklch(0.7 0.24 22 / 0.1)", borderColor: "oklch(0.7 0.24 22 / 0.3)" }}
                          >
                            <ShieldAlert className="h-3 w-3" /> Quarantine
                          </button>
                        )}
                      </div>
                    </Td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </GlassCard>

        {/* USB Scan Details */}
        <GlassCard
          title="USB Scan Details"
          subtitle={selected ? `Serial: ${selected.serialNo}` : "Select a device"}
          icon={<ShieldAlert className="h-4 w-4 text-[var(--warning)]" />}
        >
          {selected ? (
            <div className="space-y-2.5">
              <ScanRow
                icon={<FileCode2 className="h-3.5 w-3.5" />}
                label="Executable Files Found"
                value={`${selected.scan.executableFiles}`}
                valueColor={selected.scan.executableFiles > 0 ? "var(--danger)" : "var(--success)"}
              />
              <ScanRow
                icon={<EyeOff className="h-3.5 w-3.5" />}
                label="Hidden Files Found"
                value={`${selected.scan.hiddenFiles}`}
                valueColor={selected.scan.hiddenFiles > 0 ? "var(--warning)" : "var(--success)"}
              />
              <ScanRow
                icon={<Zap className="h-3.5 w-3.5" />}
                label="Autorun File"
                value={selected.scan.autorunFile ? "Yes" : "No"}
                valueColor={selected.scan.autorunFile ? "var(--danger)" : "var(--success)"}
              />

              <div className="h-px bg-gradient-to-r from-transparent via-border to-transparent" />

              <ScanRow
                icon={<ShieldAlert className="h-3.5 w-3.5" />}
                label="Scan Result"
                value={selected.scan.scanResult}
                valueColor={riskColor(selected.riskStatus)}
              />
              <ScanRow
                icon={<ShieldX className="h-3.5 w-3.5" />}
                label="Action Taken"
                value={selected.scan.actionTaken}
                valueColor={accessColor(selected.access)}
              />

              <div className="h-px bg-gradient-to-r from-transparent via-border to-transparent" />

              {/* Quick-action buttons */}
              <div className="flex gap-2 pt-1">
                <button
                  type="button"
                  disabled={!canOperateUsb || !selected}
                  className="flex flex-1 items-center justify-center gap-1.5 rounded-xl py-2 text-xs font-semibold ring-1 transition hover:brightness-125 disabled:cursor-not-allowed disabled:opacity-40"
                  style={{ color: "var(--danger)", background: "oklch(0.7 0.24 22 / 0.12)", borderColor: "oklch(0.7 0.24 22 / 0.4)" }}
                >
                  <Ban className="h-3.5 w-3.5" /> Block
                </button>
                <button
                  type="button"
                  disabled={!canOperateUsb || !selected}
                  className="flex flex-1 items-center justify-center gap-1.5 rounded-xl py-2 text-xs font-semibold ring-1 transition hover:brightness-125 disabled:cursor-not-allowed disabled:opacity-40"
                  style={{ color: "var(--warning)", background: "oklch(0.84 0.17 80 / 0.12)", borderColor: "oklch(0.84 0.17 80 / 0.4)" }}
                >
                  <ShieldAlert className="h-3.5 w-3.5" /> Quarantine
                </button>
                <button
                  type="button"
                  disabled={!canOperateUsb || !selected}
                  className="flex flex-1 items-center justify-center gap-1.5 rounded-xl py-2 text-xs font-semibold ring-1 transition hover:brightness-125 disabled:cursor-not-allowed disabled:opacity-40"
                  style={{ color: "var(--success)", background: "oklch(0.86 0.2 165 / 0.12)", borderColor: "oklch(0.86 0.2 165 / 0.4)" }}
                >
                  <CheckCircle2 className="h-3.5 w-3.5" /> Allow
                </button>
              </div>
            </div>
          ) : (
            <p className="py-8 text-center text-xs text-muted-foreground">
              Select a USB device row to view scan details.
            </p>
          )}
        </GlassCard>
      </div>
    </div>
  );
}

/* ── sub-components ─────────────────────────────────── */

function Th({ children }: { children: React.ReactNode }) {
  return <th className="px-3 py-2.5 font-medium">{children}</th>;
}

function Td({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return <td className={`px-3 py-2.5 ${className}`}>{children}</td>;
}

function RiskPill({ risk }: { risk: RiskStatus }) {
  const color = riskColor(risk);
  return (
    <span
      className="inline-flex items-center gap-1 rounded-md px-2 py-0.5 text-[10px] font-semibold ring-1"
      style={{ color, background: `${color}1f`, borderColor: `${color}55` }}
    >
      <span className="h-1.5 w-1.5 rounded-full" style={{ background: color }} />
      {risk}
    </span>
  );
}

function ScanRow({
  icon, label, value, valueColor,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
  valueColor?: string;
}) {
  return (
    <div className="glass-strong flex items-center justify-between gap-2 rounded-xl px-3 py-2.5">
      <div className="flex items-center gap-1.5 text-[11px] text-muted-foreground">
        <span style={{ color: valueColor }}>{icon}</span>
        {label}
      </div>
      <span className="text-[11px] font-semibold" style={{ color: valueColor }}>
        {value}
      </span>
    </div>
  );
}

function StatCard({
  icon, label, value, color,
}: {
  icon: React.ReactNode; label: string; value: number; color: string;
}) {
  return (
    <div className="glass relative overflow-hidden rounded-3xl p-5 shimmer-border">
      <div className="pointer-events-none absolute inset-x-6 -top-px h-px bg-gradient-to-r from-transparent via-[var(--mint)]/70 to-transparent" />
      <div className="flex h-10 w-10 items-center justify-center rounded-xl ring-1"
        style={{ background: `${color}18`, color, borderColor: `${color}40` }}>
        {icon}
      </div>
      <div className="mt-3 text-2xl font-bold tabular-nums" style={{ color }}>{value}</div>
      <div className="mt-0.5 text-xs text-muted-foreground">{label}</div>
    </div>
  );
}

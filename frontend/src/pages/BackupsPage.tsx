import { useCallback, useEffect, useRef, useState } from "react";
import axios from "axios";
import {
  DatabaseBackup, FolderOpen, Plus, Trash2, Play, RotateCcw,
  Clock, CheckCircle2, AlertTriangle, RefreshCw, Timer,
  HardDrive, Layers, ToggleLeft, ToggleRight, X,
} from "lucide-react";
import { GlassCard } from "@/components/defendra/Card";
import { useCurrentUser } from "@/hooks/useCurrentUser";

const RECOVERY_URL = "http://127.0.0.1:8001";
const recovery = axios.create({ baseURL: RECOVERY_URL, timeout: 15000 });

// ── Types ────────────────────────────────────────────────────────────────────

type Backup = {
  backup_id: string;
  label: string;
  created_at: string;
  file_count: number;
  size_bytes: number;
  paths: string[];
  exists: boolean;
  s3_uri?: string | null;
  device_id?: string;
  user_email?: string;
};

type ScheduleStatus = {
  enabled: boolean;
  interval_minutes: number;
  paths: string[];
  label: string;
  last_run_at: string | null;
  next_run_at: string | null;
  run_count: number;
  thread_alive: boolean;
};

type RestoreResult = {
  backup_id: string;
  restored_at: string;
  target: string;
  files_extracted: number;
  status: string;
};

// ── Helpers ──────────────────────────────────────────────────────────────────

function fmt(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 ** 2) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 ** 2).toFixed(2)} MB`;
}

function fmtDate(iso: string): string {
  return new Date(iso).toLocaleString();
}

function timeAgo(iso: string): string {
  const diff = Math.floor((Date.now() - new Date(iso).getTime()) / 1000);
  if (diff < 60) return `${diff}s ago`;
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  return `${Math.floor(diff / 86400)}d ago`;
}

/** Strip BOM and wrapping quotes pasted from Explorer or dialogs (matches recovery service). */
function normalizePathInput(raw: string): string {
  let p = raw.trim().replace(/\uFEFF/g, "");
  while (p.length >= 2) {
    const a = p[0]!;
    const b = p[p.length - 1]!;
    const straight = (a === '"' && b === '"') || (a === "'" && b === "'");
    const curly =
      (a === "\u201C" && b === "\u201D") ||
      (a === "\u2018" && b === "\u2019");
    if (straight || curly) {
      p = p.slice(1, -1).trim();
      continue;
    }
    break;
  }
  return p;
}

/** Get device ID from hostname (matches backend logic) */
function getDeviceId(): string {
  try {
    // Use hostname as device identifier (sanitized)
    const hostname = window.location.hostname || "unknown-device";
    const sanitized = hostname
      .toLowerCase()
      .replace(/\s+/g, "-")
      .replace(/[^a-z0-9-]/g, "");
    return sanitized || "unknown-device";
  } catch {
    return "unknown-device";
  }
}

// ── Main Component ────────────────────────────────────────────────────────────

export default function BackupsPage() {
  // Get current user for role-based filtering
  const { user, isAdmin } = useCurrentUser();
  
  // Connection to recovery service
  const [connected, setConnected] = useState(false);

  // Backup list
  const [backups, setBackups] = useState<Backup[]>([]);
  const [loadingBackups, setLoadingBackups] = useState(false);

  // Manual backup
  const [manualPaths, setManualPaths] = useState<string[]>([""]);
  const [manualLabel, setManualLabel] = useState("manual");
  const [runningBackup, setRunningBackup] = useState(false);
  const [backupResult, setBackupResult] = useState<Backup | null>(null);
  const [backupError, setBackupError] = useState("");

  // Schedule
  const [schedule, setSchedule] = useState<ScheduleStatus | null>(null);
  const [schedPaths, setSchedPaths] = useState<string[]>([""]);
  const [schedInterval, setSchedInterval] = useState(60);
  const [schedLabel, setSchedLabel] = useState("scheduled");
  const [savingSchedule, setSavingSchedule] = useState(false);
  const [scheduleMsg, setScheduleMsg] = useState("");

  // Restore
  const [restoringId, setRestoringId] = useState<string | null>(null);
  const [restoreResult, setRestoreResult] = useState<RestoreResult | null>(null);
  const [restoreError, setRestoreError] = useState("");
  const [clearingHistory, setClearingHistory] = useState(false);
  const [clearHistoryError, setClearHistoryError] = useState("");

  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // ── Health check + initial load ──────────────────────────────────────────

  const checkHealth = useCallback(async () => {
    try {
      await recovery.get("/health");
      setConnected(true);
    } catch {
      setConnected(false);
    }
  }, []);

  const fetchBackups = useCallback(async () => {
    if (!connected) return;
    setLoadingBackups(true);
    try {
      // Admin: Get ALL backups from all users/devices (no filters)
      // User: Get only backups created by this user on their device
      let url = "/backup/list";
      
      if (!isAdmin) {
        // For regular users, filter by BOTH device_id AND user_email
        const deviceId = getDeviceId();
        const userEmail = user.email;
        
        if (deviceId && userEmail) {
          url = `/backup/list?device_id=${deviceId}&user_email=${encodeURIComponent(userEmail)}`;
        } else if (deviceId) {
          // Fallback: filter by device only if email not available
          url = `/backup/list?device_id=${deviceId}`;
        }
      }
      // Admin: No filters, gets ALL backups
      
      const { data } = await recovery.get<Backup[]>(url);
      setBackups(data);
    } catch {
      // ignore
    } finally {
      setLoadingBackups(false);
    }
  }, [connected, isAdmin, user.email]);

  const fetchSchedule = useCallback(async () => {
    if (!connected) return;
    try {
      const { data } = await recovery.get<ScheduleStatus>("/backup/schedule");
      setSchedule(data);
      // Seed the form fields with current values on first load
      setSchedInterval(data.interval_minutes || 60);
      setSchedLabel(data.label || "scheduled");
      if (data.paths?.length) setSchedPaths(data.paths);
    } catch {
      // ignore
    }
  }, [connected]);

  useEffect(() => {
    checkHealth();
    const hInterval = setInterval(checkHealth, 5000);
    return () => clearInterval(hInterval);
  }, [checkHealth]);

  useEffect(() => {
    if (connected) {
      fetchBackups();
      fetchSchedule();
    }
  }, [connected, fetchBackups, fetchSchedule]);

  // Poll backup list every 10s while connected
  useEffect(() => {
    if (pollRef.current) clearInterval(pollRef.current);
    if (connected) {
      pollRef.current = setInterval(fetchBackups, 10000);
    }
    return () => { if (pollRef.current) clearInterval(pollRef.current); };
  }, [connected, fetchBackups]);

  // ── Manual backup ────────────────────────────────────────────────────────

  const addPath = () => setManualPaths((p) => [...p, ""]);
  const removePath = (i: number) => setManualPaths((p) => p.filter((_, idx) => idx !== i));
  const updatePath = (i: number, v: string) =>
    setManualPaths((p) => p.map((x, idx) => (idx === i ? v : x)));

  const runBackup = async () => {
    setRunningBackup(true);
    setBackupResult(null);
    setBackupError("");
    const paths = manualPaths.filter((p) => p.trim()).map(normalizePathInput).filter((p) => p.length > 0);
    try {
      const { data } = await recovery.post<Backup>("/backup/create", {
        paths: paths.length ? paths : null,
        label: manualLabel || "manual",
        device_id: getDeviceId(),
        user_email: user.email,
      });
      setBackupResult(data);
      await fetchBackups();
    } catch (e: any) {
      setBackupError(e?.response?.data?.detail || "Backup failed.");
    } finally {
      setRunningBackup(false);
    }
  };

  // ── Schedule ─────────────────────────────────────────────────────────────

  const addSchedPath = () => setSchedPaths((p) => [...p, ""]);
  const removeSchedPath = (i: number) => setSchedPaths((p) => p.filter((_, idx) => idx !== i));
  const updateSchedPath = (i: number, v: string) =>
    setSchedPaths((p) => p.map((x, idx) => (idx === i ? v : x)));

  const saveSchedule = async (enabled: boolean) => {
    setSavingSchedule(true);
    setScheduleMsg("");
    const paths = schedPaths.filter((p) => p.trim()).map(normalizePathInput).filter((p) => p.length > 0);
    try {
      const { data } = await recovery.post<ScheduleStatus>("/backup/schedule", {
        enabled,
        interval_minutes: schedInterval,
        paths: paths.length ? paths : null,
        label: schedLabel || "scheduled",
      });
      setSchedule(data);
      setScheduleMsg(enabled ? "Auto-backup enabled!" : "Auto-backup disabled.");
    } catch (e: any) {
      setScheduleMsg(e?.response?.data?.detail || "Failed to update schedule.");
    } finally {
      setSavingSchedule(false);
      setTimeout(() => setScheduleMsg(""), 4000);
    }
  };

  // ── Restore ──────────────────────────────────────────────────────────────

  const restoreBackup = async (backup_id: string) => {
    setRestoringId(backup_id);
    setRestoreResult(null);
    setRestoreError("");
    try {
      const { data } = await recovery.post<RestoreResult>("/backup/restore", { backup_id });
      setRestoreResult(data);
    } catch (e: any) {
      setRestoreError(e?.response?.data?.detail || "Restore failed.");
    } finally {
      setRestoringId(null);
    }
  };

  const clearBackupHistory = async () => {
    if (!connected || backups.length === 0 || clearingHistory) return;
    
    const confirmed = window.confirm(
      `Are you sure you want to permanently delete all ${backups.length} backup${backups.length !== 1 ? 's' : ''}? This action cannot be undone.`
    );
    
    if (!confirmed) return;
    
    setClearingHistory(true);
    setClearHistoryError("");
    try {
      await recovery.delete("/backup");
      setBackups([]);
      setBackupResult(null);
      setRestoreResult(null);
      setRestoreError("");
    } catch (e: any) {
      setClearHistoryError(e?.response?.data?.detail || "Failed to clear backup history.");
    } finally {
      setClearingHistory(false);
    }
  };

  // ── Render ───────────────────────────────────────────────────────────────

  const totalSize = backups.reduce((s, b) => s + b.size_bytes, 0);

  return (
    <div className="space-y-5">
      {/* Header */}
      <header className="flex flex-wrap items-end justify-between gap-3 px-1">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Backups</h1>
          <p className="text-xs text-muted-foreground">
            Manual &amp; scheduled backups · restore to any point
          </p>
        </div>
        <div className="flex items-center gap-2">
          <span
            className="flex items-center gap-1.5 rounded-xl px-3 py-1.5 text-xs font-medium ring-1"
            style={
              connected
                ? { color: "var(--success)", background: "var(--success)1f", borderColor: "var(--success)40" }
                : { color: "var(--danger)", background: "var(--danger)1f", borderColor: "var(--danger)40" }
            }
          >
            <span
              className="h-1.5 w-1.5 rounded-full"
              style={{ background: connected ? "var(--success)" : "var(--danger)" }}
            />
            Recovery service {connected ? "online" : "offline"}
          </span>
          <button
            type="button"
            onClick={fetchBackups}
            disabled={!connected}
            className="flex items-center gap-1.5 rounded-xl border border-white/10 bg-white/5 px-3 py-1.5 text-xs transition hover:bg-white/10 disabled:opacity-40"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${loadingBackups ? "animate-spin" : ""}`} />
            Refresh
          </button>
        </div>
      </header>

      {/* Stat cards */}
      <div className="grid gap-4 sm:grid-cols-3">
        <StatCard
          icon={<DatabaseBackup className="h-5 w-5" />}
          label="Total Backups"
          value={String(backups.length)}
          sub="on local storage"
          color="var(--success)"
        />
        <StatCard
          icon={<HardDrive className="h-5 w-5" />}
          label="Storage Used"
          value={fmt(totalSize)}
          sub="compressed archives"
          color="var(--cyan)"
        />
        <StatCard
          icon={<Timer className="h-5 w-5" />}
          label="Auto-Backup"
          value={schedule?.enabled ? `Every ${schedule.interval_minutes}m` : "Off"}
          sub={schedule?.last_run_at ? `Last: ${timeAgo(schedule.last_run_at)}` : "Never run"}
          color={schedule?.enabled ? "var(--mint)" : "var(--warning)"}
        />
      </div>

      {/* ── Manual Backup ──────────────────────────────────────────────────── */}
      <GlassCard
        title="Manual Backup"
        subtitle="Full Windows paths from this PC; quotes around a path are removed automatically"
        icon={<Play className="h-4 w-4 text-[var(--success)]" />}
      >
        <div className="space-y-3">
          {/* Path list */}
          <div className="space-y-2">
            {manualPaths.map((p, i) => (
              <div key={i} className="flex items-center gap-2">
                <div className="relative flex-1">
                  <FolderOpen className="pointer-events-none absolute left-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground" />
                  <input
                    type="text"
                    value={p}
                    onChange={(e) => updatePath(i, e.target.value)}
                    placeholder="C:\Users\You\Documents or C:\projects\config"
                    className="h-9 w-full rounded-xl border border-white/10 bg-white/5 pl-9 pr-3 text-sm placeholder:text-muted-foreground/50 focus:border-[var(--mint)]/50 focus:outline-none focus:ring-1 focus:ring-[var(--mint)]/20"
                  />
                </div>
                {manualPaths.length > 1 && (
                  <button
                    type="button"
                    onClick={() => removePath(i)}
                    className="flex h-9 w-9 items-center justify-center rounded-xl border border-white/10 bg-white/5 text-muted-foreground transition hover:border-[var(--danger)]/40 hover:bg-[var(--danger)]/10 hover:text-[var(--danger)]"
                  >
                    <X className="h-3.5 w-3.5" />
                  </button>
                )}
              </div>
            ))}
          </div>

          {/* Controls row */}
          <div className="flex flex-wrap items-center gap-2">
            <button
              type="button"
              onClick={addPath}
              className="flex items-center gap-1.5 rounded-xl border border-white/10 bg-white/5 px-3 py-1.5 text-xs text-muted-foreground transition hover:bg-white/10"
            >
              <Plus className="h-3.5 w-3.5" /> Add path
            </button>

            <input
              type="text"
              value={manualLabel}
              onChange={(e) => setManualLabel(e.target.value)}
              placeholder="Label (e.g. pre-update)"
              className="h-8 rounded-xl border border-white/10 bg-white/5 px-3 text-xs placeholder:text-muted-foreground/50 focus:border-[var(--mint)]/50 focus:outline-none"
            />

            <button
              type="button"
              onClick={runBackup}
              disabled={!connected || runningBackup}
              className="ml-auto flex items-center gap-2 rounded-xl bg-gradient-to-r from-[var(--mint)] to-[var(--cyan)] px-5 py-2 text-sm font-semibold text-black transition hover:brightness-110 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {runningBackup
                ? <><RefreshCw className="h-4 w-4 animate-spin" /> Running…</>
                : <><Play className="h-4 w-4" /> Run Backup Now</>}
            </button>
          </div>

          {/* Feedback */}
          {backupResult && (
            <div className="flex items-start gap-2 rounded-xl border border-[var(--success)]/30 bg-[var(--success)]/10 px-4 py-3 text-xs text-[var(--success)]">
              <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0" />
              <div>
                <span className="font-semibold">Backup complete!</span>{" "}
                ID: <code className="font-mono">{backupResult.backup_id}</code> ·{" "}
                {backupResult.file_count} file(s) · {fmt(backupResult.size_bytes)}
              </div>
            </div>
          )}
          {backupError && (
            <div className="flex items-center gap-2 rounded-xl border border-[var(--danger)]/30 bg-[var(--danger)]/10 px-4 py-2.5 text-xs text-[var(--danger)]">
              <AlertTriangle className="h-4 w-4 shrink-0" /> {backupError}
            </div>
          )}
        </div>
      </GlassCard>

      {/* ── Auto-Backup Schedule ───────────────────────────────────────────── */}
      <GlassCard
        title="Auto-Backup Schedule"
        subtitle="Automatically back up folders at a fixed interval"
        icon={<Timer className="h-4 w-4 text-[var(--cyan)]" />}
      >
        <div className="space-y-4">
          {/* Schedule status badge */}
          {schedule && (
            <div className="flex flex-wrap items-center gap-3 rounded-xl border border-white/8 bg-white/[0.03] px-4 py-3 text-xs">
              <span
                className="flex items-center gap-1.5 font-medium"
                style={{ color: schedule.enabled ? "var(--success)" : "var(--muted-foreground)" }}
              >
                {schedule.enabled
                  ? <ToggleRight className="h-4 w-4" />
                  : <ToggleLeft className="h-4 w-4" />}
                {schedule.enabled ? "Active" : "Inactive"}
              </span>
              {schedule.enabled && (
                <>
                  <span className="text-muted-foreground">Every {schedule.interval_minutes} min</span>
                  <span className="text-muted-foreground">· {schedule.run_count} run(s)</span>
                  {schedule.last_run_at && (
                    <span className="text-muted-foreground">· Last: {timeAgo(schedule.last_run_at)}</span>
                  )}
                </>
              )}
            </div>
          )}

          {/* Config form */}
          <div className="grid gap-3 sm:grid-cols-2">
            {/* Interval */}
            <div className="space-y-1.5">
              <label className="text-[11px] font-medium uppercase tracking-wider text-muted-foreground">
                Interval (minutes)
              </label>
              <div className="flex items-center gap-2">
                <input
                  type="number"
                  min={1}
                  value={schedInterval}
                  onChange={(e) => setSchedInterval(Math.max(1, Number(e.target.value)))}
                  className="h-9 w-28 rounded-xl border border-white/10 bg-white/5 px-3 text-sm tabular-nums focus:border-[var(--mint)]/50 focus:outline-none"
                />
                <div className="flex gap-1.5">
                  {[1, 5, 15, 30, 60].map((v) => (
                    <button
                      key={v}
                      type="button"
                      onClick={() => setSchedInterval(v)}
                      className="rounded-lg px-2 py-1 text-[11px] ring-1 transition hover:brightness-125"
                      style={
                        schedInterval === v
                          ? { color: "var(--cyan)", background: "oklch(0.86 0.2 165/0.15)", borderColor: "oklch(0.86 0.2 165/0.4)" }
                          : { color: "var(--muted-foreground)", background: "transparent", borderColor: "rgba(255,255,255,0.1)" }
                      }
                    >
                      {v < 60 ? `${v}m` : "1h"}
                    </button>
                  ))}
                </div>
              </div>
            </div>

            {/* Label */}
            <div className="space-y-1.5">
              <label className="text-[11px] font-medium uppercase tracking-wider text-muted-foreground">
                Backup label
              </label>
              <input
                type="text"
                value={schedLabel}
                onChange={(e) => setSchedLabel(e.target.value)}
                placeholder="scheduled"
                className="h-9 w-full rounded-xl border border-white/10 bg-white/5 px-3 text-sm placeholder:text-muted-foreground/50 focus:border-[var(--mint)]/50 focus:outline-none"
              />
            </div>
          </div>

          {/* Paths */}
          <div className="space-y-1.5">
            <label className="text-[11px] font-medium uppercase tracking-wider text-muted-foreground">
              Folders to watch (leave empty to use server defaults)
            </label>
            <div className="space-y-2">
              {schedPaths.map((p, i) => (
                <div key={i} className="flex items-center gap-2">
                  <div className="relative flex-1">
                    <FolderOpen className="pointer-events-none absolute left-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground" />
                    <input
                      type="text"
                      value={p}
                      onChange={(e) => updateSchedPath(i, e.target.value)}
                      placeholder="C:\Users\You\Documents"
                      className="h-9 w-full rounded-xl border border-white/10 bg-white/5 pl-9 pr-3 text-sm placeholder:text-muted-foreground/50 focus:border-[var(--mint)]/50 focus:outline-none"
                    />
                  </div>
                  {schedPaths.length > 1 && (
                    <button
                      type="button"
                      onClick={() => removeSchedPath(i)}
                      className="flex h-9 w-9 items-center justify-center rounded-xl border border-white/10 bg-white/5 text-muted-foreground transition hover:border-[var(--danger)]/40 hover:bg-[var(--danger)]/10 hover:text-[var(--danger)]"
                    >
                      <X className="h-3.5 w-3.5" />
                    </button>
                  )}
                </div>
              ))}
              <button
                type="button"
                onClick={addSchedPath}
                className="flex items-center gap-1.5 rounded-xl border border-white/10 bg-white/5 px-3 py-1.5 text-xs text-muted-foreground transition hover:bg-white/10"
              >
                <Plus className="h-3.5 w-3.5" /> Add folder
              </button>
            </div>
          </div>

          {/* Action buttons */}
          <div className="flex flex-wrap items-center gap-2">
            <button
              type="button"
              onClick={() => saveSchedule(true)}
              disabled={!connected || savingSchedule}
              className="flex items-center gap-2 rounded-xl bg-gradient-to-r from-[var(--mint)] to-[var(--cyan)] px-5 py-2 text-sm font-semibold text-black transition hover:brightness-110 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {savingSchedule ? <RefreshCw className="h-4 w-4 animate-spin" /> : <ToggleRight className="h-4 w-4" />}
              Enable Auto-Backup
            </button>
            <button
              type="button"
              onClick={() => saveSchedule(false)}
              disabled={!connected || savingSchedule || !schedule?.enabled}
              className="flex items-center gap-2 rounded-xl border border-[var(--danger)]/30 bg-[var(--danger)]/10 px-5 py-2 text-sm font-semibold text-[var(--danger)] transition hover:bg-[var(--danger)]/20 disabled:cursor-not-allowed disabled:opacity-40"
            >
              <ToggleLeft className="h-4 w-4" /> Disable
            </button>
            {scheduleMsg && (
              <span className="text-xs" style={{ color: scheduleMsg.includes("!") ? "var(--success)" : "var(--warning)" }}>
                {scheduleMsg}
              </span>
            )}
          </div>
        </div>
      </GlassCard>

      {/* ── Backup History ─────────────────────────────────────────────────── */}
      <GlassCard
        title="Backup History"
        subtitle={`${backups.length} saved backup(s)`}
        icon={<Layers className="h-4 w-4 text-[var(--mint)]" />}
        action={
          <button
            type="button"
            disabled={!connected || backups.length === 0 || clearingHistory}
            onClick={clearBackupHistory}
            className="flex items-center gap-1.5 rounded-xl border border-[var(--danger)]/30 bg-[var(--danger)]/10 px-3 py-1.5 text-xs font-medium text-[var(--danger)] transition hover:bg-[var(--danger)]/20 disabled:cursor-not-allowed disabled:opacity-40"
          >
            <Trash2 className={`h-3.5 w-3.5 ${clearingHistory ? "animate-pulse" : ""}`} />
            Clear All
          </button>
        }
      >
        {/* Restore feedback */}
        {restoreResult && (
          <div className="mb-3 flex items-start gap-2 rounded-xl border border-[var(--success)]/30 bg-[var(--success)]/10 px-4 py-3 text-xs text-[var(--success)]">
            <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0" />
            <div>
              <span className="font-semibold">Restore complete!</span>{" "}
              {restoreResult.files_extracted} file(s) → <code className="font-mono">{restoreResult.target}</code>
            </div>
            <button onClick={() => setRestoreResult(null)} className="ml-auto"><X className="h-3.5 w-3.5" /></button>
          </div>
        )}
        {restoreError && (
          <div className="mb-3 flex items-center gap-2 rounded-xl border border-[var(--danger)]/30 bg-[var(--danger)]/10 px-4 py-2.5 text-xs text-[var(--danger)]">
            <AlertTriangle className="h-4 w-4 shrink-0" /> {restoreError}
            <button onClick={() => setRestoreError("")} className="ml-auto"><X className="h-3.5 w-3.5" /></button>
          </div>
        )}
        {clearHistoryError && (
          <div className="mb-3 flex items-center gap-2 rounded-xl border border-[var(--danger)]/30 bg-[var(--danger)]/10 px-4 py-2.5 text-xs text-[var(--danger)]">
            <AlertTriangle className="h-4 w-4 shrink-0" /> {clearHistoryError}
            <button onClick={() => setClearHistoryError("")} className="ml-auto"><X className="h-3.5 w-3.5" /></button>
          </div>
        )}

        <div className="overflow-hidden rounded-xl ring-1 ring-white/5">
          <table className="w-full text-left text-xs">
            <thead className="bg-white/5 text-[10px] uppercase tracking-wider text-muted-foreground">
              <tr>
                <Th>Backup ID</Th>
                <Th>Label</Th>
                <Th>Created</Th>
                <Th>Files</Th>
                <Th>Size</Th>
                <Th>Paths</Th>
                <Th>Action</Th>
              </tr>
            </thead>
            <tbody>
              {backups.length === 0 && (
                <tr>
                  <td colSpan={7} className="px-3 py-10 text-center text-muted-foreground">
                    {connected ? "No backups yet. Create one above." : "Recovery service is offline."}
                  </td>
                </tr>
              )}
              {backups.map((b) => (
                <tr key={b.backup_id} className="border-t border-white/5 transition hover:bg-white/[0.03]">
                  <Td>
                    <code className="font-mono text-[10px] text-[var(--cyan)]">
                      {b.backup_id.slice(0, 16)}…
                    </code>
                  </Td>
                  <Td>
                    <span
                      className="inline-flex items-center gap-1 rounded-md px-2 py-0.5 text-[10px] font-medium ring-1"
                      style={{
                        color: b.label === "scheduled" ? "var(--mint)" : "var(--cyan)",
                        background: b.label === "scheduled" ? "oklch(0.86 0.2 165/0.1)" : "oklch(0.86 0.2 200/0.1)",
                        borderColor: b.label === "scheduled" ? "oklch(0.86 0.2 165/0.3)" : "oklch(0.86 0.2 200/0.3)",
                      }}
                    >
                      {b.label}
                    </span>
                  </Td>
                  <Td>
                    <span className="inline-flex items-center gap-1 tabular-nums text-muted-foreground">
                      <Clock className="h-3 w-3" /> {fmtDate(b.created_at)}
                    </span>
                  </Td>
                  <Td className="tabular-nums">{b.file_count}</Td>
                  <Td className="tabular-nums text-muted-foreground">{fmt(b.size_bytes)}</Td>
                  <Td>
                    <div className="max-w-[200px] truncate text-muted-foreground">
                      {b.paths.join(", ") || "—"}
                    </div>
                  </Td>
                  <Td>
                    <button
                      type="button"
                      disabled={!b.exists || restoringId === b.backup_id || !connected}
                      onClick={() => restoreBackup(b.backup_id)}
                      className="flex items-center gap-1 rounded-lg px-2.5 py-1 text-[10px] font-medium ring-1 transition hover:brightness-125 disabled:cursor-not-allowed disabled:opacity-40"
                      style={{
                        color: "var(--success)",
                        background: "oklch(0.86 0.2 165/0.1)",
                        borderColor: "oklch(0.86 0.2 165/0.3)",
                      }}
                    >
                      {restoringId === b.backup_id
                        ? <><RefreshCw className="h-3 w-3 animate-spin" /> Restoring…</>
                        : <><RotateCcw className="h-3 w-3" /> Restore</>}
                    </button>
                  </Td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </GlassCard>
    </div>
  );
}

// ── Sub-components ────────────────────────────────────────────────────────────

function Th({ children }: { children: React.ReactNode }) {
  return <th className="px-3 py-2.5 font-medium">{children}</th>;
}

function Td({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return <td className={`px-3 py-2.5 ${className}`}>{children}</td>;
}

function StatCard({
  icon, label, value, sub, color,
}: {
  icon: React.ReactNode; label: string; value: string; sub: string; color: string;
}) {
  return (
    <div className="glass relative overflow-hidden rounded-3xl p-5 shimmer-border">
      <div className="pointer-events-none absolute inset-x-6 -top-px h-px bg-gradient-to-r from-transparent via-[var(--mint)]/70 to-transparent" />
      <div className="flex items-start justify-between gap-3">
        <div
          className="flex h-10 w-10 items-center justify-center rounded-xl ring-1"
          style={{ background: `${color}18`, color, borderColor: `${color}40` }}
        >
          {icon}
        </div>
        <span className="h-2 w-2 mt-1">
          <span className="block h-2 w-2 rounded-full animate-pulse" style={{ background: color }} />
        </span>
      </div>
      <div className="mt-3 text-xl font-bold tabular-nums" style={{ color }}>{value}</div>
      <div className="text-sm font-medium">{label}</div>
      <div className="mt-0.5 text-xs text-muted-foreground">{sub}</div>
    </div>
  );
}

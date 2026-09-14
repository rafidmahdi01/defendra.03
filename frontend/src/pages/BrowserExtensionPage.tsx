import { useState } from "react";
import {
  Download,
  Chrome,
  CheckCircle2,
  AlertCircle,
  ExternalLink,
  Copy,
  Shield,
  Eye,
  Layers,
  Zap,
} from "lucide-react";
import { GlassCard } from "@/components/defendra/Card";

export default function BrowserExtensionPage() {
  const [copied, setCopied] = useState(false);

  const extensionPath = window.location.origin.replace(/:\d+$/, "") + "/extension";
  const chromeExtensionsUrl = "chrome://extensions";

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const openExtensionFolder = () => {
    // This will attempt to open the extension folder
    window.open(`${window.location.origin}/extension`, '_blank');
  };

  return (
    <div className="space-y-5">
      {/* Header */}
      <header className="px-1">
        <h1 className="text-2xl font-semibold tracking-tight">Browser Extension</h1>
        <p className="text-xs text-muted-foreground">
          Real-time web threat detection · monitor phishing attempts · detect malicious overlays
        </p>
      </header>

      {/* Quick Stats */}
      <div className="grid gap-4 sm:grid-cols-4">
        <StatCard
          icon={<Shield className="h-5 w-5" />}
          label="Protection Level"
          value="Real-time"
          color="var(--success)"
        />
        <StatCard
          icon={<Eye className="h-5 w-5" />}
          label="Monitoring"
          value="All Pages"
          color="var(--cyan)"
        />
        <StatCard
          icon={<Layers className="h-5 w-5" />}
          label="Detection Types"
          value="4 Threats"
          color="var(--mint)"
        />
        <StatCard
          icon={<Zap className="h-5 w-5" />}
          label="Status"
          value="Ready"
          color="var(--electric)"
        />
      </div>

      {/* Installation Instructions */}
      <GlassCard
        title="Quick Installation"
        subtitle="Install the browser extension in 3 simple steps"
        icon={<Download className="h-4 w-4 text-[var(--mint)]" />}
      >
        <div className="space-y-6">
          {/* Step 1 */}
          <div className="flex gap-4">
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-gradient-to-r from-[var(--mint)] to-[var(--cyan)] text-lg font-bold text-black">
              1
            </div>
            <div className="flex-1 space-y-3">
              <h3 className="font-semibold">Open Browser Extensions Page</h3>
              <p className="text-sm text-muted-foreground">
                Open your browser's extension management page
              </p>
              <div className="flex flex-wrap gap-2">
                <button
                  onClick={() => copyToClipboard(chromeExtensionsUrl)}
                  className="flex items-center gap-2 rounded-xl border border-white/10 bg-white/5 px-4 py-2.5 text-sm transition hover:bg-white/10"
                >
                  <Chrome className="h-4 w-4" />
                  <code className="font-mono text-xs">{chromeExtensionsUrl}</code>
                  <Copy className="h-3.5 w-3.5 ml-1" />
                </button>
                {copied && (
                  <span className="flex items-center gap-1.5 text-xs text-[var(--success)]">
                    <CheckCircle2 className="h-3.5 w-3.5" /> Copied!
                  </span>
                )}
              </div>
              <div className="rounded-lg border border-[var(--cyan)]/30 bg-[var(--cyan)]/10 px-3 py-2 text-xs text-[var(--cyan)]">
                <strong>Chrome/Edge:</strong> Paste <code className="font-mono">chrome://extensions</code> in the address bar
              </div>
            </div>
          </div>

          <div className="h-px bg-gradient-to-r from-transparent via-border to-transparent" />

          {/* Step 2 */}
          <div className="flex gap-4">
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-gradient-to-r from-[var(--mint)] to-[var(--cyan)] text-lg font-bold text-black">
              2
            </div>
            <div className="flex-1 space-y-3">
              <h3 className="font-semibold">Enable Developer Mode</h3>
              <p className="text-sm text-muted-foreground">
                Toggle the "Developer mode" switch in the top-right corner
              </p>
              <div className="rounded-lg border border-white/10 bg-white/5 p-4">
                <img
                  src="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='400' height='60' viewBox='0 0 400 60'%3E%3Crect width='400' height='60' fill='%23ffffff08'/%3E%3Ctext x='20' y='35' font-family='Arial' font-size='14' fill='%23a1a1aa'%3EDeveloper mode%3C/text%3E%3Crect x='340' y='22' width='40' height='16' rx='8' fill='%2300d9b8'/%3E%3Ccircle cx='368' cy='30' r='6' fill='%23000000'/%3E%3C/svg%3E"
                  alt="Developer mode toggle"
                  className="w-full max-w-md rounded-lg"
                />
              </div>
            </div>
          </div>

          <div className="h-px bg-gradient-to-r from-transparent via-border to-transparent" />

          {/* Step 3 */}
          <div className="flex gap-4">
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-gradient-to-r from-[var(--mint)] to-[var(--cyan)] text-lg font-bold text-black">
              3
            </div>
            <div className="flex-1 space-y-3">
              <h3 className="font-semibold">Load Extension Folder</h3>
              <p className="text-sm text-muted-foreground">
                Click "Load unpacked" and navigate to the extension folder
              </p>
              <div className="space-y-2">
                <div className="rounded-lg border border-white/10 bg-white/5 px-3 py-2">
                  <div className="text-[11px] font-medium uppercase tracking-wider text-muted-foreground mb-2">
                    Extension Path
                  </div>
                  <code className="break-all text-xs font-mono text-[var(--cyan)]">
                    D:\defendra-main\defendra-main\extension
                  </code>
                </div>
                <button
                  onClick={openExtensionFolder}
                  className="flex items-center gap-2 rounded-xl bg-gradient-to-r from-[var(--mint)] to-[var(--cyan)] px-5 py-2.5 text-sm font-semibold text-black transition hover:brightness-110"
                >
                  <ExternalLink className="h-4 w-4" />
                  Open Extension Folder
                </button>
              </div>
            </div>
          </div>

          {/* Success Message */}
          <div className="rounded-xl border border-[var(--success)]/30 bg-[var(--success)]/10 px-4 py-3">
            <div className="flex items-start gap-3">
              <CheckCircle2 className="h-5 w-5 shrink-0 text-[var(--success)]" />
              <div className="text-sm">
                <div className="font-semibold text-[var(--success)]">Installation Complete!</div>
                <p className="mt-1 text-xs text-[var(--success)]/80">
                  Once installed, the extension icon will appear in your browser toolbar. Click it to view detected threats and configure settings.
                </p>
              </div>
            </div>
          </div>
        </div>
      </GlassCard>

      {/* Features */}
      <GlassCard
        title="What It Detects"
        subtitle="Real-time monitoring for browser-based threats"
        icon={<Eye className="h-4 w-4 text-[var(--cyan)]" />}
      >
        <div className="grid gap-4 sm:grid-cols-2">
          <FeatureCard
            icon={<Layers className="h-5 w-5 text-[var(--danger)]" />}
            title="Large Overlays"
            description="Detects suspicious overlays covering >60% of the screen, common in phishing attacks and scareware"
          />
          <FeatureCard
            icon={<Shield className="h-5 w-5 text-[var(--warning)]" />}
            title="Dynamic Password Fields"
            description="Alerts when password inputs are added after page load, indicating credential harvesting attempts"
          />
          <FeatureCard
            icon={<AlertCircle className="h-5 w-5 text-[var(--electric)]" />}
            title="Suspicious Text Patterns"
            description="Identifies social engineering phrases like 'Update your browser' or 'Verify your payment'"
          />
          <FeatureCard
            icon={<Zap className="h-5 w-5 text-[var(--mint)]" />}
            title="DOM Churn Detection"
            description="Monitors rapid page changes (>150 mutations/sec) that suggest obfuscation or malicious content"
          />
        </div>
      </GlassCard>

      {/* How It Works */}
      <GlassCard
        title="How It Works"
        subtitle="Seamless integration with Defendra backend"
        icon={<Chrome className="h-4 w-4 text-[var(--mint)]" />}
      >
        <div className="space-y-4">
          <div className="rounded-lg border border-white/10 bg-white/5 p-4">
            <div className="flex items-start gap-3">
              <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-[var(--cyan)]/20 text-[var(--cyan)]">
                1
              </div>
              <div>
                <h4 className="font-medium">Content Script Monitors Web Pages</h4>
                <p className="mt-1 text-xs text-muted-foreground">
                  Runs on every page you visit, using heuristics to detect suspicious behavior in real-time
                </p>
              </div>
            </div>
          </div>

          <div className="rounded-lg border border-white/10 bg-white/5 p-4">
            <div className="flex items-start gap-3">
              <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-[var(--mint)]/20 text-[var(--mint)]">
                2
              </div>
              <div>
                <h4 className="font-medium">Background Service Processes Events</h4>
                <p className="mt-1 text-xs text-muted-foreground">
                  Stores up to 200 events locally, shows desktop notifications, and forwards to Defendra backend
                </p>
              </div>
            </div>
          </div>

          <div className="rounded-lg border border-white/10 bg-white/5 p-4">
            <div className="flex items-start gap-3">
              <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-[var(--success)]/20 text-[var(--success)]">
                3
              </div>
              <div>
                <h4 className="font-medium">Events Appear in Your Dashboard</h4>
                <p className="mt-1 text-xs text-muted-foreground">
                  View all browser threats in the Logs page, filtered by "browser-monitor" category
                </p>
              </div>
            </div>
          </div>
        </div>
      </GlassCard>

      {/* Privacy Notice */}
      <div className="rounded-xl border border-[var(--warning)]/30 bg-[var(--warning)]/10 px-4 py-3">
        <div className="flex items-start gap-3">
          <AlertCircle className="h-5 w-5 shrink-0 text-[var(--warning)]" />
          <div className="text-sm">
            <div className="font-semibold text-[var(--warning)]">Privacy & Security Note</div>
            <p className="mt-1 text-xs text-[var(--warning)]/80">
              This extension does not take automatic screenshots. Screen capture only occurs when you explicitly click "Capture screen" in the extension popup and grant permission. All events are stored locally first, then optionally sent to your local Defendra backend at 127.0.0.1:8000.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

// Helper Components
function StatCard({
  icon,
  label,
  value,
  color,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
  color: string;
}) {
  return (
    <div className="glass relative overflow-hidden rounded-2xl p-4">
      <div className="pointer-events-none absolute inset-x-4 -top-px h-px bg-gradient-to-r from-transparent via-[var(--mint)]/50 to-transparent" />
      <div
        className="flex h-9 w-9 items-center justify-center rounded-lg ring-1"
        style={{ background: `${color}18`, color, borderColor: `${color}40` }}
      >
        {icon}
      </div>
      <div className="mt-3 text-lg font-bold" style={{ color }}>
        {value}
      </div>
      <div className="text-xs font-medium text-muted-foreground">{label}</div>
    </div>
  );
}

function FeatureCard({
  icon,
  title,
  description,
}: {
  icon: React.ReactNode;
  title: string;
  description: string;
}) {
  return (
    <div className="rounded-xl border border-white/10 bg-white/5 p-4">
      <div className="mb-3">{icon}</div>
      <h3 className="mb-2 font-semibold">{title}</h3>
      <p className="text-xs text-muted-foreground">{description}</p>
    </div>
  );
}

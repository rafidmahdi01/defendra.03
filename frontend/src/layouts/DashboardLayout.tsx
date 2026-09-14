import { Outlet } from "react-router-dom";
import { WifiOff } from "lucide-react";

import { AIAssistantWidget } from "@/components/defendra/AIAssistant";
import { AppFooter } from "@/components/defendra/AppFooter";
import { CursorFx } from "@/components/defendra/CursorFx";
import { Particles } from "@/components/defendra/Particles";
import { TopBar } from "@/components/defendra/TopBar";
import { WorkstationHeartbeat } from "@/components/defendra/WorkstationHeartbeat";
import { WorkstationLinkGate } from "@/components/defendra/WorkstationLinkGate";
import { ServiceConnectedProvider, useServiceConnected } from "@/hooks/useServiceConnected";

function ConnectionBanner() {
  const { connected, checking } = useServiceConnected();
  if (connected) return null;
  return (
    <div
      className="flex items-center gap-2 border-b border-[var(--danger)]/25 bg-[var(--danger)]/10 px-6 py-2 text-[11px] text-[var(--danger)]"
      role="status"
    >
      <WifiOff className="h-3.5 w-3.5 shrink-0" />
      <span>
        {checking
          ? "Checking connection to the protection server…"
          : "Not connected to the protection server. Actions stay disabled until the connection is restored."}
      </span>
    </div>
  );
}

export default function DashboardLayout() {
  return (
    <ServiceConnectedProvider>
      <WorkstationHeartbeat />
      <WorkstationLinkGate>
        <div className="relative min-h-screen text-foreground">
          <CursorFx />
          <Particles />
          <div className="flex flex-col min-h-screen">
            <TopBar />
            <ConnectionBanner />
            <main className="flex-1 px-6 py-5">
              <Outlet />
            </main>
            <AppFooter />
          </div>
          <AIAssistantWidget />
        </div>
      </WorkstationLinkGate>
    </ServiceConnectedProvider>
  );
}

import React from "react";
import ReactDOM from "react-dom/client";
import { HashRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Toaster } from "sonner";

import App from "./App";
import { TelemetryProvider } from "@/hooks/useTelemetry";
import "./styles.css";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { staleTime: 30_000, refetchOnWindowFocus: false },
  },
});

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <TelemetryProvider intervalMs={30000}>
        <HashRouter>
          <App />
        </HashRouter>
        <Toaster richColors theme="dark" position="top-right" />
      </TelemetryProvider>
    </QueryClientProvider>
  </React.StrictMode>,
);

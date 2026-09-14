import { lazy, Suspense } from "react";
import { Navigate, Outlet, Route, Routes } from "react-router-dom";

import DashboardLayout from "@/layouts/DashboardLayout";

const LoginPage            = lazy(() => import("@/pages/LoginPage"));
const RegisterPage         = lazy(() => import("@/pages/RegisterPage"));
const Dashboard            = lazy(() => import("@/pages/Dashboard"));
const DevicesPage          = lazy(() => import("@/pages/DevicesPage"));
const EmailsPage           = lazy(() => import("@/pages/EmailsPage"));
const UsbPage              = lazy(() => import("@/pages/UsbPage"));
const BackupsPage          = lazy(() => import("@/pages/BackupsPage"));
const BrowserExtensionPage = lazy(() => import("@/pages/BrowserExtensionPage"));
const AlertsPage           = lazy(() => import("@/pages/AlertsPage"));
const AnalyticsPage        = lazy(() => import("@/pages/AnalyticsPage"));
const LogsPage             = lazy(() => import("@/pages/LogsPage"));
const SettingsPage         = lazy(() => import("@/pages/SettingsPage"));
const WhitelistPage        = lazy(() => import("@/pages/WhitelistPage"));

function ProtectedRoute() {
  const token = localStorage.getItem("crps_token");
  return token ? <Outlet /> : <Navigate to="/login" replace />;
}

function PageLoader() {
  return (
    <div className="flex h-64 items-center justify-center">
      <div className="h-6 w-6 animate-spin rounded-full border-2 border-[var(--mint)] border-t-transparent" />
    </div>
  );
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Suspense fallback={<PageLoader />}><LoginPage /></Suspense>} />
      <Route path="/register" element={<Suspense fallback={<PageLoader />}><RegisterPage /></Suspense>} />
      <Route element={<ProtectedRoute />}>
        <Route element={<DashboardLayout />}>
          <Route path="/" element={<Suspense fallback={<PageLoader />}><Dashboard /></Suspense>} />
          <Route path="/devices" element={<Suspense fallback={<PageLoader />}><DevicesPage /></Suspense>} />
          <Route path="/emails" element={<Suspense fallback={<PageLoader />}><EmailsPage /></Suspense>} />
          <Route path="/usb" element={<Suspense fallback={<PageLoader />}><UsbPage /></Suspense>} />
          <Route path="/backups" element={<Suspense fallback={<PageLoader />}><BackupsPage /></Suspense>} />
          <Route path="/extension" element={<Suspense fallback={<PageLoader />}><BrowserExtensionPage /></Suspense>} />
          <Route path="/alerts" element={<Suspense fallback={<PageLoader />}><AlertsPage /></Suspense>} />
          <Route path="/analytics" element={<Suspense fallback={<PageLoader />}><AnalyticsPage /></Suspense>} />
          <Route path="/logs" element={<Suspense fallback={<PageLoader />}><LogsPage /></Suspense>} />
          <Route path="/settings" element={<Suspense fallback={<PageLoader />}><SettingsPage /></Suspense>} />
          <Route path="/whitelist" element={<Suspense fallback={<PageLoader />}><WhitelistPage /></Suspense>} />
        </Route>
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

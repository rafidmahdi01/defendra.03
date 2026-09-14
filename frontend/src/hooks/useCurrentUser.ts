import { useCallback, useEffect, useState } from "react";

export type CrpsUser = {
  id?: string;
  email?: string;
  full_name?: string;
  role?: string;
};

export const AUTH_CHANGED_EVENT = "crps-auth-changed";

export function readStoredUser(): CrpsUser {
  try {
    return JSON.parse(localStorage.getItem("crps_user") || "{}") as CrpsUser;
  } catch {
    return {};
  }
}

export function notifyAuthChanged(): void {
  window.dispatchEvent(new Event(AUTH_CHANGED_EVENT));
}

export function formatUserRole(role?: string): string {
  const r = (role || "").toLowerCase();
  if (r === "admin") return "Admin";
  if (r === "user") return "User";
  return role || "User";
}

export function isAdminRole(role?: string): boolean {
  return (role || "").toLowerCase() === "admin";
}

export function useCurrentUser() {
  const [user, setUser] = useState<CrpsUser>(() => readStoredUser());

  const refresh = useCallback(() => {
    setUser(readStoredUser());
  }, []);

  useEffect(() => {
    const onAuthChange = () => refresh();
    window.addEventListener(AUTH_CHANGED_EVENT, onAuthChange);
    window.addEventListener("storage", onAuthChange);
    return () => {
      window.removeEventListener(AUTH_CHANGED_EVENT, onAuthChange);
      window.removeEventListener("storage", onAuthChange);
    };
  }, [refresh]);

  return {
    user,
    isAdmin: isAdminRole(user.role),
    displayName: user.full_name || user.email || "User",
    roleLabel: formatUserRole(user.role),
    refresh,
  };
}

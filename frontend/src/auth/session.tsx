import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import api, { logout } from "../services/api";
import type { SessionUser } from "./types";

type AuthValue = {
  user: SessionUser | null;
  ready: boolean;
  can: (permission: string) => boolean;
  refreshSession: () => void;
  signOut: () => void;
};

const AuthContext = createContext<AuthValue | null>(null);

export function AuthProvider({
  children,
  initialUser,
}: {
  children: ReactNode;
  initialUser?: SessionUser | null;
}) {
  const fixed = initialUser !== undefined;
  const [user, setUser] = useState<SessionUser | null>(fixed ? initialUser : null);
  const [ready, setReady] = useState(fixed || !localStorage.getItem("access"));
  const [tick, setTick] = useState(0);

  useEffect(() => {
    if (fixed) return;
    const token = localStorage.getItem("access");
    if (!token) {
      setUser(null);
      setReady(true);
      return;
    }
    let cancel = false;
    setReady(false);
    api
      .get<SessionUser>("/users/me/")
      .then((response) => {
        if (!cancel) setUser(normalizeUser(response.data));
      })
      .catch(() => {
        if (!cancel) {
          logout();
          setUser(null);
        }
      })
      .finally(() => {
        if (!cancel) setReady(true);
      });
    return () => {
      cancel = true;
    };
  }, [fixed, tick]);

  const can = useCallback(
    (permission: string) => {
      if (!user) return false;
      if (user.is_superuser) return true;
      return user.permissions.includes(permission);
    },
    [user],
  );

  const value = useMemo<AuthValue>(
    () => ({
      user,
      ready,
      can,
      refreshSession: () => setTick((current) => current + 1),
      signOut: () => {
        logout();
        setUser(null);
        setReady(true);
      },
    }),
    [user, ready, can],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

function normalizeUser(data: SessionUser): SessionUser {
  return {
    ...data,
    permissions: data.permissions ?? [],
    is_superuser: Boolean(data.is_superuser),
    can_own_client: Boolean(data.can_own_client),
    can_be_assigned_recruiter: Boolean(data.can_be_assigned_recruiter),
  };
}

export function useAuth() {
  const value = useContext(AuthContext);
  if (!value) throw new Error("useAuth must be used inside AuthProvider");
  return value;
}

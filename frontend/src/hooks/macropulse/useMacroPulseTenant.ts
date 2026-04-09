"use client";

import { useEffect, useState } from "react";

export const MACROPULSE_TENANT_KEY = "macropulse-demo-tenant-id";
export const DEFAULT_MACROPULSE_TENANT_ID = "demo-in-001";

export function useMacroPulseTenant() {
  const [tenantId, setTenantIdState] = useState(DEFAULT_MACROPULSE_TENANT_ID);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    try {
      const stored = window.localStorage.getItem(MACROPULSE_TENANT_KEY);
      if (stored) {
        setTenantIdState(stored);
      } else {
        window.localStorage.setItem(MACROPULSE_TENANT_KEY, DEFAULT_MACROPULSE_TENANT_ID);
      }
    } finally {
      setReady(true);
    }
  }, []);

  const setTenantId = (value: string) => {
    const next = value.trim() || DEFAULT_MACROPULSE_TENANT_ID;
    setTenantIdState(next);
    try {
      window.localStorage.setItem(MACROPULSE_TENANT_KEY, next);
    } catch {
      // Ignore local storage issues.
    }
  };

  return { tenantId, setTenantId, ready };
}

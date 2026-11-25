import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { api, type PrioritizationRow } from "../lib/api";

export const DEMO_ACCOUNTS = {
  c36: "Company 36 B2B",
  c37: "Company 37 Cloud",
  acme: "Acme Technologies",
  fintech: "Fintech Pulse Inc",
} as const;
export type DemoKey = keyof typeof DEMO_ACCOUNTS;

interface DemoState { active: boolean; step: number }
interface DemoApi extends DemoState {
  start: (step?: number) => void;
  go: (step: number) => void;
  exit: () => void;
  accounts: Partial<Record<DemoKey, PrioritizationRow>>;
  accountsError: string | null;
  preload: () => void;
  ready: boolean;
}

const KEY = "gtmos-demo-tour";
const Ctx = createContext<DemoApi | null>(null);

function read(): DemoState {
  try {
    const raw = window.sessionStorage.getItem(KEY);
    if (raw) {
      const s = JSON.parse(raw) as DemoState;
      if (typeof s.active === "boolean" && Number.isInteger(s.step)) return { active: s.active, step: Math.min(5, Math.max(0, s.step)) };
    }
  } catch { /* storage unavailable: start fresh */ }
  return { active: false, step: 0 };
}

export function DemoProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<DemoState>(read);
  const [accounts, setAccounts] = useState<Partial<Record<DemoKey, PrioritizationRow>>>({});
  const [accountsError, setAccountsError] = useState<string | null>(null);
  const [loaded, setLoaded] = useState(false);
  const [wanted, setWanted] = useState(false);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    try { window.sessionStorage.setItem(KEY, JSON.stringify(state)); } catch { /* memory only */ }
  }, [state]);

  // Resolve demo accounts by name once a tour starts; ids are never hard-coded.
  useEffect(() => {
    if (!(state.active || wanted) || loaded) return;
    setLoaded(true);
    api.prioritization()
      .then((rows) => {
        const found: Partial<Record<DemoKey, PrioritizationRow>> = {};
        (Object.keys(DEMO_ACCOUNTS) as DemoKey[]).forEach((k) => {
          const row = rows.find((r) => r.name === DEMO_ACCOUNTS[k]);
          if (row) found[k] = row;
        });
        setAccounts(found);
        setReady(true);
      })
      .catch((e: unknown) => { setAccountsError(e instanceof Error ? e.message : String(e)); setReady(true); });
  }, [state.active, wanted, loaded]);

  const start = useCallback((step = 0) => setState({ active: true, step }), []);
  const go = useCallback((step: number) => setState({ active: true, step: Math.min(5, Math.max(0, step)) }), []);
  const exit = useCallback(() => setState({ active: false, step: 0 }), []);
  const preload = useCallback(() => setWanted(true), []);

  const value = useMemo(() => ({ ...state, start, go, exit, accounts, accountsError, preload, ready }),
    [state, start, go, exit, accounts, accountsError, preload, ready]);
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useDemo(): DemoApi {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error("useDemo must be used inside DemoProvider");
  return ctx;
}

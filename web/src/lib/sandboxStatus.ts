import { useSyncExternalStore } from "react";

/**
 * Detects when this browser's temporary demo sandbox has disappeared.
 *
 * The server reports on each guarded response whether a sandbox exists for this
 * browser on the server that answered (X-Demo-Sandbox) and which one (X-Demo-Sandbox-Id).
 * After an edit we remember that id. If a later response says "none" or a different id,
 * the edits made in the old sandbox are no longer visible, and we tell the visitor.
 */
export type SandboxLoss = { kind: "missing" | "recreated"; at: number } | null;

const KEY = "gtmos-demo-sandbox-id";
const LOSS_KEY = "gtmos-demo-sandbox-loss";   // keeps the notice across reloads until dismissed
let memoryId: string | null = null;
let loss: SandboxLoss = readLoss();

function readLoss(): SandboxLoss {
  try {
    const raw = window.sessionStorage.getItem(LOSS_KEY);
    const v = raw ? (JSON.parse(raw) as SandboxLoss) : null;
    return v && (v.kind === "missing" || v.kind === "recreated") ? v : null;
  } catch { return null; }
}
const listeners = new Set<() => void>();

function getExpected(): string | null {
  try { return window.localStorage.getItem(KEY); } catch { return memoryId; }
}
function setExpected(id: string | null) {
  memoryId = id;
  try { if (id) window.localStorage.setItem(KEY, id); else window.localStorage.removeItem(KEY); } catch { /* memory only */ }
}
function emit(next: SandboxLoss) {
  loss = next;
  try { if (next) window.sessionStorage.setItem(LOSS_KEY, JSON.stringify(next)); else window.sessionStorage.removeItem(LOSS_KEY); } catch { /* memory only */ }
  listeners.forEach((l) => l());
}

/** Call after every API response from the public demo. */
export function observeSandbox(res: Response, opts: { mutating: boolean; intentionalReset?: boolean }) {
  const state = res.headers.get("x-demo-sandbox");
  if (!state) return;                       // routes outside the guard, or the full local API
  const id = res.headers.get("x-demo-sandbox-id");
  if (opts.intentionalReset) { setExpected(null); if (loss) emit(null); return; }
  const expected = getExpected();
  if (expected) {
    if (state === "none") { setExpected(null); emit({ kind: "missing", at: Date.now() }); return; }
    if (id && id !== expected) { setExpected(id); emit({ kind: "recreated", at: Date.now() }); return; }
    return;
  }
  if (state === "active" && id) setExpected(id);   // start tracking (after an edit, or a sandbox we didn't know about)
}

export function dismissSandboxLoss() { emit(null); }

export function useSandboxLoss(): SandboxLoss {
  return useSyncExternalStore(
    (cb) => { listeners.add(cb); return () => listeners.delete(cb); },
    () => loss,
    () => null,
  );
}

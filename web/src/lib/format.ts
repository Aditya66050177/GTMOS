import type { Action, Tier } from "./api";

export const SIGNAL_LABEL: Record<string, string> = {
  support_hiring: "Support hiring",
  funding: "Funding",
  product_launch: "Product launch",
  international_expansion: "International expansion",
  relevant_technology: "Relevant tech",
  rapid_growth: "Rapid growth",
  executive_change: "Executive change",
  too_small: "Too small",
  wrong_industry: "Wrong industry",
  wrong_geography: "Wrong geography",
  no_use_case: "No use case",
};

export const signalLabel = (t: string | null | undefined) => (t ? SIGNAL_LABEL[t] ?? t.replace(/_/g, " ") : "—");

export const TIER_STYLE: Record<Tier, string> = {
  "Priority 1": "border-signal-400/40 bg-signal-400/10 text-signal-300",
  "Priority 2": "border-sky-400/40 bg-sky-400/10 text-sky-400",
  "Priority 3": "border-amberx-400/40 bg-amberx-400/10 text-amberx-400",
  Low: "border-ink-600 bg-ink-800 text-mist-400",
};

export const ACTION_STYLE: Record<Action, string> = {
  CONTACT: "bg-signal-400 text-ink-950 border-transparent",
  PRIORITIZE: "bg-sky-400 text-ink-950 border-transparent",
  NURTURE: "border-amberx-400/50 text-amberx-400 bg-amberx-400/10",
  RESEARCH: "border-mist-500/50 text-mist-300 bg-ink-800",
  DEPRIORITIZE: "border-ink-600 text-mist-500 bg-ink-850",
};

export function scoreColor(score: number): string {
  if (score >= 90) return "#4DFFAE";
  if (score >= 75) return "#5CC8FF";
  if (score >= 50) return "#FFC857";
  return "#6E788C";
}

export function shortDate(iso: string | null | undefined): string {
  if (!iso) return "—";
  const d = new Date(iso.endsWith("Z") || iso.includes("+") ? iso : `${iso}Z`);
  return d.toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" });
}

export function daysAgo(iso: string | null | undefined): string {
  if (!iso) return "";
  const d = new Date(iso.endsWith("Z") || iso.includes("+") ? iso : `${iso}Z`);
  const days = Math.max(0, Math.round((Date.now() - d.getTime()) / 86_400_000));
  return days === 0 ? "today" : days === 1 ? "1 day ago" : `${days} days ago`;
}

export const pct = (n: number) => `${Math.round(n * 10) / 10}%`;

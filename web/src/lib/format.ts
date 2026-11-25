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

// Tiers are ordinal, so they use one hue at decreasing strength, then neutral.
export const TIER_STYLE: Record<Tier, string> = {
  "Priority 1": "border-accent-600 bg-accent-600 text-white",
  "Priority 2": "border-accent-100 bg-accent-50 text-accent-700",
  "Priority 3": "border-line-strong bg-surface text-ink-2",
  Low: "border-neutral-200 bg-neutral-100 text-ink-4",
};

// Action colours follow urgency: act now (accent) > wait (warn) > look (neutral) > drop (muted).
export const ACTION_STYLE: Record<Action, string> = {
  CONTACT: "border-accent-600 bg-accent-600 text-white",
  PRIORITIZE: "border-accent-600 bg-accent-50 text-accent-700",
  NURTURE: "border-warn-200 bg-warn-50 text-warn-700",
  RESEARCH: "border-line-strong bg-surface text-ink-2",
  DEPRIORITIZE: "border-neutral-200 bg-neutral-100 text-ink-4",
};

// Tier distribution: sequential accent ramp, Low in neutral grey.
export const TIER_FILL: Record<Tier, string> = {
  "Priority 1": "#134E4A",
  "Priority 2": "#0F766E",
  "Priority 3": "#2DD4BF",
  Low: "#D0D5DD",
};

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

import { observeSandbox } from "./sandboxStatus";

export type Tier = "Priority 1" | "Priority 2" | "Priority 3" | "Low";
export type Action = "CONTACT" | "PRIORITIZE" | "NURTURE" | "RESEARCH" | "DEPRIORITIZE";

export interface ICP {
  industries: string[];
  company_size_min: number;
  company_size_max: number;
  geographies: string[];
  buyer_roles: string[];
  pain_points: string[];
  technologies: string[];
  buying_triggers: string[];
  exclusions: string[];
}

export interface AccountRow {
  id: number;
  name: string;
  domain: string | null;
  industry: string | null;
  employee_count: number | null;
  country: string | null;
  stage: string;
  total_score: number;
  tier: Tier;
  intent_score: number;
  action: Action | null;
  top_signal: string | null;
}

export interface Overview {
  product: { name: string; description: string };
  icp: ICP | null;
  llm_mode: string;
  counts: { accounts: number; signals: number; rejected_claims: number; pending_drafts: number; won: number };
  tiers: Record<Tier, number>;
  stages: Record<string, number>;
  top_accounts: AccountRow[];
}

export interface SignalItem {
  id?: number;
  type: string;
  description: string;
  evidence: string;
  source: string;
  detected_at?: string | null;
  confidence: number;
  strength?: number;
  negative: boolean;
}

export interface Component { component: string; score: number; max_score: number }
export interface Reason { rule: string; met: boolean; text: string; points: number }
export interface Recommendation { action: Action; reason: string; suggested_persona: string | null; suggested_angle: string | null }

export interface DraftItem {
  id: number;
  account_id: number;
  account_name: string;
  account_stage: string | null;
  body: string;
  original_body: string;
  edited: boolean;
  status: "pending" | "approved" | "rejected" | "sent";
  evidence: SignalItem[];
  created_at: string | null;
  reviewed_at: string | null;
}

export interface AccountDetail {
  account: AccountRow & { description: string | null; technology_stack: string[]; funding: string | null; support_team_size: number | null };
  score: { total: number; tier: Tier; components: Component[]; reasons: Reason[] } | null;
  recommendation: Recommendation | null;
  signals: SignalItem[];
  contacts: { id: number; name: string; role: string | null; email: string | null }[];
  drafts: DraftItem[];
  activities: { id: number; type: string; status: string; timestamp: string | null; metadata: Record<string, unknown> }[];
}

export interface PlaygroundInput {
  name: string;
  industry: string;
  employee_count: number;
  country: string;
  description: string;
  technology_stack: string[];
  research_note: string;
}

export interface PlaygroundResult {
  score: {
    total_score: number; tier: Tier; icp_fit: number; company_fit: number; technology_fit: number;
    intent_score: number; geography_score: number; components: Component[]; reasons: Reason[];
  };
  recommendation: Recommendation;
  signals: SignalItem[];
  note_had_text: boolean;
}

export interface Funnel {
  totals: { total_accounts: number; high_priority_accounts: number; contacted: number; replies: number; meetings: number; opportunities: number; won: number; lost: number };
  stage_counts: Record<string, number>;
  conversions: { from_stage: string; to_stage: string; from_count: number; to_count: number; conversion_rate_pct: number }[];
  performance_by_tier: Record<string, unknown>[];
  performance_by_industry: Record<string, unknown>[];
  performance_by_angle: Record<string, unknown>[];
}

export interface Trends { weekly_trends: { week: string; contacted: number; replies: number; meetings: number; opportunities: number; won: number }[] }
export interface AskResponse {
  question: string; function_called: string; explanation: string; data: unknown;
  observations?: string[]; hypotheses?: string[]; data_label?: string | null; generated_by?: string;
}

export interface ExecutiveAnswer {
  question_id: string; question: string; summary: string;
  observations: { text: string }[]; hypotheses: { text: string; label: string }[];
  accounts: { id: number; name: string; stage: string | null; tier: Tier | null; total: number | null; fit: number | null;
    intent: number | null; action: Action | null; rule_id: string | null; why: string[]; evidence: string | null;
    uses_synthetic_demo_additions: boolean }[];
  data: Record<string, unknown>; selection_rules: string[]; data_sources: string[];
  data_provenance: Record<string, string>; data_quality: string[]; generated_by: string;
}
export interface ExecutiveQuestionRef { id: string; question: string; endpoint: string }

export interface Methodology {
  components: { name: string; max: number; part_of: "fit" | "intent"; rule: string }[];
  fit_max: number; intent_max: number;
  signal_weights: Record<string, number>; disqualifier_penalties: Record<string, number>;
  decay: { current_max_days: number; aging_max_days: number; aging_decay: number };
  tiers: { tier: Tier; min_total: number }[];
  action_rules: { rule_id: string; tier: string; condition: string; action: Action }[];
  rejection_categories: Record<string, string>;
  evaluation: {
    tier: { accuracy: number; correct: number; total: number; precision: Record<string, number>; recall: Record<string, number>;
      confusion_matrix: Record<string, Record<string, number>>; method: string };
    signals: { precision: number; recall: number; f1: number; total: number; unsupported_claim_rate: number; method: string };
  };
}

export interface PipelineResp {
  total_accounts: number;
  stages: Record<string, { stage: string; count: number; accounts: { id: number; name: string; industry: string | null; tier: Tier; total_score: number; deal_value: number | null }[] }>;
}

export interface EvidenceCounts { current: number; aging: number; expired: number; superseded: number; rejected: number }
export interface PrioritizationRow {
  id: number; name: string; industry: string | null; country: string | null; employee_count: number | null;
  stage: string; scored: boolean; fit: number | null; intent: number | null; total: number | null;
  tier: Tier | null; action: Action | null; rule_id: string | null; evidence: EvidenceCounts;
  uses_synthetic_demo_additions: boolean;
}

export type SignalStatus = "current" | "aging" | "expired" | "superseded" | "disqualifier" | "not_weighted";
export interface Contribution {
  signal_id: number; signal_type: string; label: string; status: SignalStatus; counted: boolean;
  source: string | null; detected_at: string | null; days_old: number; quote: string | null; source_sentence: string | null;
  weight: number; strength: number; confidence: number; decay: number; points: number; why_it_matters: string | null;
}
export interface RejectedEvidence {
  sentence: string | null; category: string; reason: string | null; claimed_type: string | null;
  source: string | null; date: string | null; dataset: string | null; points: number;
}
export interface Explanation {
  account: { id: number; name: string; industry: string | null; employee_count: number | null; country: string | null; stage: string | null };
  data_label: string;
  fit: { score: number; max_score: number; meaning: string; components: { name: string; score: number; max_score: number; reasons: Reason[] }[] };
  intent: {
    score: number; max_score: number; meaning: string; raw_total: number; clamped: boolean; recomputed_score: number;
    matches_stored_score: boolean; as_of: string; buying_signals: Contribution[]; disqualifiers: Contribution[];
    recency_rules: { current_max_days: number; aging_max_days: number; aging_decay: number; formula: string };
  };
  total: { total: number; max_score: number; tier: Tier; rule: string };
  recommendation: { action: Action; rule_id: string; rule: string; reason: string; suggested_persona: string | null; suggested_angle: string | null };
  disqualification_reasons: string[];
  rejected_evidence: RejectedEvidence[];
  research_notes: { source: string | null; date: string | null; dataset: string | null; label: string | null; raw_text: string | null; signals_extracted: number }[];
  evidence_summary: { buying_signals: number; counted: number; current: number; aging: number; expired: number; superseded: number; disqualifiers: number; rejected: number };
  includes_synthetic_demo_additions: boolean;
}
export interface Comparison { accounts: Explanation[]; observations: string[] }
export interface FeaturedComparison { title: string; selection_rule: string; account_ids: number[] }

export class ApiError extends Error {}

// A random, per-browser id that keeps this visitor's demo edits in a private
// sandbox on the server. It identifies nothing about the person.
const SESSION_KEY = "gtmos-demo-session";
let memorySession: string | null = null;

function newSessionId(): string {
  const bytes = new Uint8Array(16);
  crypto.getRandomValues(bytes);
  return Array.from(bytes, (b) => b.toString(16).padStart(2, "0")).join("");
}

export function demoSessionId(): string {
  try {
    const stored = window.localStorage.getItem(SESSION_KEY);
    if (stored && /^[a-f0-9]{32}$/.test(stored)) return stored;
    const fresh = newSessionId();
    window.localStorage.setItem(SESSION_KEY, fresh);
    return fresh;
  } catch {
    memorySession ??= newSessionId();
    return memorySession;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`/api${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", "X-Demo-Session": demoSessionId() },
  });
  const method = (init?.method ?? "GET").toUpperCase();
  observeSandbox(res, { mutating: method !== "GET", intentionalReset: path === "/web/reset" && res.ok });
  if (!res.ok) {
    let detail = `${res.status} ${res.statusText}`;
    try {
      const body = await res.json();
      if (body?.detail) detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail);
    } catch { /* keep status text */ }
    throw new ApiError(detail);
  }
  return res.json() as Promise<T>;
}

const post = <T>(path: string, body?: unknown) =>
  request<T>(path, { method: "POST", body: body === undefined ? undefined : JSON.stringify(body) });

export const api = {
  overview: () => request<Overview>("/web/overview"),
  accounts: () => request<AccountRow[]>("/web/accounts"),
  account: (id: number) => request<AccountDetail>(`/web/accounts/${id}`),
  explain: (id: number) => request<Explanation>(`/web/accounts/${id}/explain`),
  compare: (ids: number[]) => request<Comparison>(`/web/compare?ids=${ids.join(",")}`),
  featured: () => request<FeaturedComparison[]>("/web/comparisons/featured"),
  prioritization: () => request<PrioritizationRow[]>("/web/prioritization"),
  methodology: () => request<Methodology>("/web/methodology"),
  executiveQuestions: () => request<ExecutiveQuestionRef[]>("/web/executive"),
  executive: (id: string) => request<ExecutiveAnswer>(`/web/executive/${id}`),
  drafts: () => request<DraftItem[]>("/web/drafts"),
  playground: (input: PlaygroundInput) => post<PlaygroundResult>("/web/playground", input),
  reset: () => post<{ status: string; had_changes: boolean }>("/web/reset"),
  personalize: (id: number) => post<unknown>(`/accounts/${id}/personalize`),
  editDraft: (id: number, body: string) => request<unknown>(`/drafts/${id}`, { method: "PATCH", body: JSON.stringify({ body }) }),
  approveDraft: (id: number) => post<unknown>(`/drafts/${id}/approve`),
  rejectDraft: (id: number) => post<unknown>(`/drafts/${id}/reject`),
  markSent: (accountId: number, draftId: number) => post<unknown>(`/accounts/${accountId}/mark_sent?draft_id=${draftId}`),
  funnel: () => request<Funnel>("/analytics/funnel"),
  trends: () => request<Trends>("/analytics/trends"),
  ask: (question: string) => post<AskResponse>("/analytics/ask", { question }),
  pipeline: () => request<PipelineResp>("/pipeline"),
};

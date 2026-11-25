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
export interface AskResponse { question: string; function_called: string; explanation: string; data: unknown }

export interface PipelineResp {
  total_accounts: number;
  stages: Record<string, { stage: string; count: number; accounts: { id: number; name: string; industry: string | null; tier: Tier; total_score: number; deal_value: number | null }[] }>;
}

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

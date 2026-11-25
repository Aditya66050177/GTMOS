import { useState } from "react";
import { Link } from "react-router-dom";
import { Check, Pencil, X } from "lucide-react";
import { api, type DraftItem } from "../lib/api";
import { useAsync } from "../lib/useAsync";
import { EmptyState, ErrorBox, Loading, PageHeader } from "../components/ui";
import { shortDate, signalLabel } from "../lib/format";

const TABS: { key: DraftItem["status"]; label: string }[] = [
  { key: "pending", label: "Pending" },
  { key: "approved", label: "Approved" },
  { key: "sent", label: "Logged as sent" },
  { key: "rejected", label: "Rejected" },
];

const STATUS_LABEL: Record<DraftItem["status"], string> = {
  pending: "awaiting review",
  approved: "approved — not sent",
  sent: "logged as sent by a person",
  rejected: "rejected",
};

const STATUS_STYLE: Record<DraftItem["status"], string> = {
  pending: "border-warn-200 bg-warn-50 text-warn-700",
  approved: "border-accent-100 bg-accent-50 text-accent-700",
  sent: "border-line-strong bg-surface text-ink-2",
  rejected: "border-neutral-200 bg-neutral-100 text-ink-4",
};

function DraftCard({ draft, onChange }: { draft: DraftItem; onChange: () => Promise<unknown> }) {
  const [editing, setEditing] = useState(false);
  const [body, setBody] = useState(draft.body);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [showOriginal, setShowOriginal] = useState(false);
  const words = body.trim().split(/\s+/).filter(Boolean).length;

  async function act(fn: () => Promise<unknown>) {
    setBusy(true); setErr(null);
    try { await fn(); await onChange(); }
    catch (e) { setErr(e instanceof Error ? e.message : String(e)); }
    finally { setBusy(false); }
  }

  return (
    <article className="panel overflow-hidden">
      <header className="panel-head">
        <div className="flex min-w-0 flex-wrap items-center gap-2">
          <Link to={`/app/accounts/${draft.account_id}`} className="font-semibold text-ink hover:text-accent-700 hover:underline">{draft.account_name}</Link>
          <span className={`badge ${STATUS_STYLE[draft.status]}`}>{STATUS_LABEL[draft.status]}</span>
          {draft.evidence[0] && <span className="badge border-line-strong bg-surface text-ink-2">Signal: {signalLabel(draft.evidence[0].type)}</span>}
          {draft.edited && <span className="badge border-line-strong bg-surface text-ink-3">edited by reviewer</span>}
        </div>
        <span className="text-xs text-ink-4">Stage: {draft.account_stage}</span>
      </header>

      <div className="grid lg:grid-cols-[1.35fr_1fr]">
        <div className="p-4 sm:p-5">
          {editing ? (
            <>
              <label className="label" htmlFor={`d-${draft.id}`}>Edit draft</label>
              <textarea id={`d-${draft.id}`} className="input min-h-[220px] leading-relaxed" value={body} onChange={(e) => setBody(e.target.value)} />
              <div className={`num mt-1 text-xs ${words > 120 ? "text-danger-700" : "text-ink-4"}`}>{words} / 120 words</div>
            </>
          ) : (
            <pre className="whitespace-pre-wrap font-sans text-sm leading-relaxed text-ink">{draft.body}</pre>
          )}
          {draft.edited && !editing && (
            <button className="mt-3 text-xs font-medium text-accent-700 hover:underline" onClick={() => setShowOriginal((v) => !v)} aria-expanded={showOriginal}>
              {showOriginal ? "Hide" : "Show"} the original AI draft
            </button>
          )}
          {showOriginal && <pre className="mt-2 whitespace-pre-wrap rounded-md border border-line bg-subtle p-3 font-sans text-xs leading-relaxed text-ink-3">{draft.original_body}</pre>}
        </div>

        <aside className="border-t border-line bg-subtle p-4 sm:p-5 lg:border-l lg:border-t-0">
          <div className="eyebrow">Evidence behind this draft</div>
          <ul className="mt-2 space-y-3">
            {draft.evidence.map((e) => (
              <li key={e.id} className="border-l-[3px] border-accent-600 pl-3">
                <div className="text-xs font-semibold text-ink-2">{signalLabel(e.type)} · {e.source}{e.detected_at ? ` · ${shortDate(e.detected_at)}` : ""}</div>
                <div className="mt-0.5 text-ink-2">“{e.evidence}”</div>
              </li>
            ))}
            {draft.evidence.length === 0 && <li className="text-ink-3">No signals: the draft may only use profile facts.</li>}
          </ul>
          <p className="mt-3 text-2xs text-ink-4">The fact-check refused any number not found in this evidence or the account profile.</p>
          <Link to={`/app/accounts/${draft.account_id}`} className="mt-1 inline-block text-xs font-medium text-accent-700 hover:underline">Inspect the full evidence and scoring</Link>
        </aside>
      </div>

      <footer className="flex flex-wrap items-center gap-2 border-t border-line px-4 py-3 sm:px-5">
        {draft.status === "pending" && !editing && (
          <>
            <button className="btn-primary" disabled={busy} onClick={() => act(() => api.approveDraft(draft.id))}><Check className="h-4 w-4" aria-hidden /> Approve</button>
            <button className="btn-secondary" disabled={busy} onClick={() => setEditing(true)}><Pencil className="h-4 w-4" aria-hidden /> Edit</button>
            <button className="btn-danger" disabled={busy} onClick={() => act(() => api.rejectDraft(draft.id))}><X className="h-4 w-4" aria-hidden /> Reject</button>
          </>
        )}
        {editing && (
          <>
            <button className="btn-primary" disabled={busy || !body.trim()} onClick={() => act(async () => { await api.editDraft(draft.id, body); setEditing(false); })}>Save edit</button>
            <button className="btn-secondary" disabled={busy} onClick={() => { setBody(draft.body); setEditing(false); }}>Cancel</button>
          </>
        )}
        {draft.status === "approved" && (
          <>
            <button className="btn-primary" disabled={busy} onClick={() => act(() => api.markSent(draft.account_id, draft.id))}>I sent it myself — log it</button>
            <span className="text-xs text-ink-3">GTMOS never sends email. A person sends it, then logs it here.</span>
          </>
        )}
        {draft.status === "sent" && <span className="text-ink-3">Logged as sent by a person. The account moved to Contacted.</span>}
        {draft.status === "rejected" && <span className="text-ink-3">Rejected. Nothing was sent.</span>}
        {err && <span className="w-full text-xs text-danger-700" role="alert">{err}</span>}
      </footer>
    </article>
  );
}

export default function ReviewPage() {
  const { data, error, loading, reload } = useAsync(api.drafts);
  const [tab, setTab] = useState<DraftItem["status"]>("pending");

  if (loading && !data) return <Loading />;
  if (error || !data) return <ErrorBox message={error ?? "No data returned."} onRetry={reload} />;
  const items = data.filter((d) => d.status === tab);

  return (
    <div>
      <PageHeader eyebrow="Human in the loop" title="Review queue"
        description="Every AI draft lands here first. Numbers not found in the evidence were already refused by the fact-check, and nothing leaves until a person approves and sends it." />
      <div className="segmented mb-4 overflow-x-auto" role="group" aria-label="Filter drafts by status">
        {TABS.map((t) => (
          <button key={t.key} type="button" aria-pressed={tab === t.key} onClick={() => setTab(t.key)} className="whitespace-nowrap">
            {t.label} <span className="num text-ink-4">{data.filter((d) => d.status === t.key).length}</span>
          </button>
        ))}
      </div>
      <div className="space-y-4">
        {items.map((d) => <DraftCard key={`${d.id}-${d.status}-${d.body.length}`} draft={d} onChange={reload} />)}
        {items.length === 0 && (
          <EmptyState title={`No ${TABS.find((t) => t.key === tab)?.label.toLowerCase()} drafts`}>
            {tab === "pending" && <>Open a <Link className="font-medium text-accent-700 hover:underline" to="/app/accounts?tier=Priority+2">Priority 2 account</Link> and draft one from its evidence.</>}
          </EmptyState>
        )}
      </div>
    </div>
  );
}

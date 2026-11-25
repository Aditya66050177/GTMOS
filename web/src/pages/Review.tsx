import { useState } from "react";
import { Link } from "react-router-dom";
import { Check, Mail, Pencil, ShieldCheck, X } from "lucide-react";
import { api, type DraftItem } from "../lib/api";
import { useAsync } from "../lib/useAsync";
import { ErrorBox, Loading, PageHeader } from "../components/ui";
import { signalLabel } from "../lib/format";

const TABS: { key: DraftItem["status"]; label: string }[] = [
  { key: "pending", label: "Pending" },
  { key: "approved", label: "Approved" },
  { key: "sent", label: "Sent" },
  { key: "rejected", label: "Rejected" },
];

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
    <article className="card overflow-hidden">
      <header className="flex flex-wrap items-center gap-3 border-b border-ink-800 px-5 py-4">
        <Mail className="h-4 w-4 text-mist-400" />
        <Link to={`/app/accounts/${draft.account_id}`} className="font-semibold hover:text-signal-300">{draft.account_name}</Link>
        {draft.edited && <span className="chip border-amberx-400/40 bg-amberx-400/10 text-amberx-400">edited by reviewer</span>}
        <span className="ml-auto text-xs text-mist-500">Stage: {draft.account_stage}</span>
      </header>

      <div className="grid gap-0 lg:grid-cols-[1.3fr_1fr]">
        <div className="p-5">
          {editing ? (
            <>
              <label className="label" htmlFor={`d-${draft.id}`}>Edit draft</label>
              <textarea id={`d-${draft.id}`} className="input min-h-[220px] font-mono text-[13px] leading-relaxed" value={body} onChange={(e) => setBody(e.target.value)} />
              <div className={`mt-1 text-xs ${words > 120 ? "text-rose-400" : "text-mist-500"}`}>{words} / 120 words</div>
            </>
          ) : (
            <pre className="whitespace-pre-wrap font-sans text-sm leading-relaxed text-mist-100">{draft.body}</pre>
          )}
          {draft.edited && !editing && (
            <button className="mt-3 text-xs text-mist-400 underline-offset-2 hover:underline" onClick={() => setShowOriginal((v) => !v)}>
              {showOriginal ? "Hide" : "Show"} the original AI draft
            </button>
          )}
          {showOriginal && <pre className="mt-2 whitespace-pre-wrap rounded-xl border border-ink-700 bg-ink-850 p-3 font-sans text-xs leading-relaxed text-mist-400">{draft.original_body}</pre>}
        </div>

        <aside className="border-t border-ink-800 bg-ink-850/50 p-5 lg:border-l lg:border-t-0">
          <div className="flex items-center gap-2 text-xs font-semibold text-signal-300"><ShieldCheck className="h-4 w-4" /> Grounded in {draft.evidence.length} verified signal{draft.evidence.length === 1 ? "" : "s"}</div>
          <ul className="mt-3 space-y-3">
            {draft.evidence.map((e) => (
              <li key={e.id} className="text-sm">
                <div className="text-xs font-medium text-mist-300">{signalLabel(e.type)} · {e.source}</div>
                <div className="mt-0.5 text-mist-400">“{e.evidence}”</div>
              </li>
            ))}
            {draft.evidence.length === 0 && <li className="text-sm text-mist-400">No signals: the draft may only use profile facts.</li>}
          </ul>
        </aside>
      </div>

      <footer className="flex flex-wrap items-center gap-2 border-t border-ink-800 px-5 py-4">
        {draft.status === "pending" && !editing && (
          <>
            <button className="btn-primary" disabled={busy} onClick={() => act(() => api.approveDraft(draft.id))}><Check className="h-4 w-4" /> Approve</button>
            <button className="btn-ghost" disabled={busy} onClick={() => setEditing(true)}><Pencil className="h-4 w-4" /> Edit</button>
            <button className="btn-danger" disabled={busy} onClick={() => act(() => api.rejectDraft(draft.id))}><X className="h-4 w-4" /> Reject</button>
          </>
        )}
        {editing && (
          <>
            <button className="btn-primary" disabled={busy || !body.trim()} onClick={() => act(async () => { await api.editDraft(draft.id, body); setEditing(false); })}>Save edit</button>
            <button className="btn-ghost" disabled={busy} onClick={() => { setBody(draft.body); setEditing(false); }}>Cancel</button>
          </>
        )}
        {draft.status === "approved" && (
          <>
            <button className="btn-primary" disabled={busy} onClick={() => act(() => api.markSent(draft.account_id, draft.id))}>I sent it — log it</button>
            <span className="text-xs text-mist-500">GTMOS never sends email. A human sends it, then logs it here.</span>
          </>
        )}
        {draft.status === "sent" && <span className="text-sm text-mist-400">Logged as sent. The account moved to Contacted.</span>}
        {draft.status === "rejected" && <span className="text-sm text-mist-400">Rejected. Nothing was sent.</span>}
        {err && <span className="w-full text-xs text-rose-400">{err}</span>}
      </footer>
    </article>
  );
}

export default function ReviewPage() {
  const { data, error, loading, reload } = useAsync(api.drafts);
  const [tab, setTab] = useState<DraftItem["status"]>("pending");

  if (loading && !data) return <Loading />;
  if (error || !data) return <ErrorBox message={error ?? "No data"} onRetry={reload} />;
  const items = data.filter((d) => d.status === tab);

  return (
    <div>
      <PageHeader eyebrow="Human in the loop" title="Review queue" />
      <p className="-mt-3 mb-6 max-w-3xl text-sm text-mist-400">
        Every AI draft lands here first. Numbers that aren't in the evidence were already refused by the fact-check, and
        nothing leaves until a person approves it.
      </p>
      <div className="mb-5 flex gap-1 overflow-x-auto rounded-xl border border-ink-700 bg-ink-900 p-1 sm:inline-flex">
        {TABS.map((t) => {
          const count = data.filter((d) => d.status === t.key).length;
          return (
            <button key={t.key} onClick={() => setTab(t.key)}
              className={`flex items-center gap-2 whitespace-nowrap rounded-lg px-3 py-1.5 text-sm font-medium ${tab === t.key ? "bg-ink-700 text-mist-100" : "text-mist-400 hover:text-mist-100"}`}>
              {t.label} <span className="font-mono text-xs text-mist-500">{count}</span>
            </button>
          );
        })}
      </div>
      <div className="space-y-4">
        {items.map((d) => <DraftCard key={`${d.id}-${d.status}-${d.body.length}`} draft={d} onChange={reload} />)}
        {items.length === 0 && (
          <div className="card card-pad text-center text-sm text-mist-400">
            Nothing {tab} right now.{" "}
            {tab === "pending" && <>Open a <Link className="text-signal-400 underline" to="/app/accounts?tier=Priority+2">Priority 2 account</Link> and draft one.</>}
          </div>
        )}
      </div>
    </div>
  );
}

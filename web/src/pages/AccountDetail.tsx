import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ArrowLeft, Check, Minus, Sparkles, UserRound } from "lucide-react";
import { api } from "../lib/api";
import { useAsync } from "../lib/useAsync";
import { ActionBadge, ComponentBars, ErrorBox, EvidenceCard, Loading, ScoreRing, TierBadge } from "../components/ui";
import { shortDate } from "../lib/format";

const ACTIVITY_LABEL: Record<string, string> = {
  outreach_sent: "Outreach sent", reply_received: "Reply received", meeting_held: "Meeting held",
  opportunity_created: "Opportunity created", deal_won: "Deal won", deal_lost: "Deal lost",
  outreach_approved: "Draft approved", stage_change: "Stage changed", rejected_signal: "Claim rejected",
};

export default function AccountDetailPage() {
  const id = Number(useParams().id);
  const { data, error, loading, reload } = useAsync(() => api.account(id), [id]);
  const [drafting, setDrafting] = useState(false);
  const [draftError, setDraftError] = useState<string | null>(null);

  async function generateDraft() {
    setDrafting(true);
    setDraftError(null);
    try { await api.personalize(id); await reload(); }
    catch (e) { setDraftError(e instanceof Error ? e.message : String(e)); }
    finally { setDrafting(false); }
  }

  if (loading && !data) return <Loading />;
  if (error || !data) return <ErrorBox message={error ?? "No data"} onRetry={reload} />;
  const { account, score, recommendation: rec } = data;
  const positives = data.signals.filter((s) => !s.negative);
  const negatives = data.signals.filter((s) => s.negative);
  const blocked = rec?.action === "DEPRIORITIZE";
  const pendingDraft = data.drafts.find((d) => d.status === "pending");

  return (
    <div>
      <Link to="/app/accounts" className="mb-5 inline-flex items-center gap-1 text-sm text-mist-400 hover:text-mist-100">
        <ArrowLeft className="h-4 w-4" /> Accounts
      </Link>

      <div className="card card-pad flex flex-col gap-6 sm:flex-row sm:items-center">
        {score && <ScoreRing score={score.total} />}
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <h1 className="h-display text-2xl sm:text-3xl">{account.name}</h1>
            <TierBadge tier={account.tier} />
          </div>
          <div className="mt-1 text-sm text-mist-400">
            {[account.industry, `${account.employee_count} employees`, account.country, account.funding, account.domain].filter(Boolean).join(" · ")}
          </div>
          {account.description && <p className="mt-3 max-w-2xl text-sm text-mist-300">{account.description}</p>}
          {account.technology_stack.length > 0 && (
            <div className="mt-3 flex flex-wrap gap-1.5">
              {account.technology_stack.map((t) => <span key={t} className="chip border-ink-600 bg-ink-850 text-mist-300">{t}</span>)}
            </div>
          )}
        </div>
        <div className="rounded-xl border border-ink-700 bg-ink-850 px-4 py-3 text-sm">
          <div className="text-xs text-mist-500">Pipeline stage</div>
          <div className="mt-0.5 font-semibold">{account.stage}</div>
        </div>
      </div>

      <div className="mt-4 grid gap-4 lg:grid-cols-[1.1fr_0.9fr]">
        {score && (
          <div className="card card-pad">
            <h2 className="font-display text-lg font-semibold">Why this score</h2>
            <p className="mt-1 text-sm text-mist-400">Deterministic: the same account and ICP always give the same result.</p>
            <div className="mt-5"><ComponentBars components={score.components} /></div>
            <ul className="mt-6 space-y-2.5 border-t border-ink-800 pt-5">
              {score.reasons.map((r, i) => (
                <li key={`${r.rule}-${i}`} className="flex gap-3 text-sm">
                  <span className={`mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full ${r.met ? "bg-signal-400/15 text-signal-400" : "bg-ink-800 text-mist-500"}`}>
                    {r.met ? <Check className="h-3 w-3" /> : <Minus className="h-3 w-3" />}
                  </span>
                  <div className="min-w-0 flex-1">
                    <span className="font-medium">{r.rule}</span>
                    <span className="text-mist-400"> — {r.text}</span>
                  </div>
                  <span className="font-mono tabular-nums text-mist-300">+{r.points.toFixed(1)}</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        <div className="space-y-4">
          {rec && (
            <div className="card card-pad">
              <div className="flex items-center justify-between">
                <h2 className="font-display text-lg font-semibold">Recommended next action</h2>
                <ActionBadge action={rec.action} />
              </div>
              <p className="mt-3 text-sm text-mist-300">{rec.reason}</p>
              <dl className="mt-4 grid grid-cols-2 gap-3 text-sm">
                <div><dt className="label">Persona</dt><dd>{rec.suggested_persona ?? "—"}</dd></div>
                <div><dt className="label">Angle</dt><dd>{rec.suggested_angle ?? "—"}</dd></div>
              </dl>
              <div className="mt-5 border-t border-ink-800 pt-5">
                {pendingDraft ? (
                  <Link to="/app/review" className="btn-primary w-full">Review the pending draft</Link>
                ) : (
                  <button className="btn-primary w-full" disabled={blocked || drafting} onClick={generateDraft}>
                    <Sparkles className="h-4 w-4" /> {drafting ? "Drafting…" : "Draft outreach from evidence"}
                  </button>
                )}
                {blocked && <p className="mt-2 text-xs text-mist-500">Deprioritized accounts can't get outreach drafts. The rule table blocks it, not the LLM.</p>}
                {draftError && <p className="mt-2 text-xs text-rose-400">{draftError}</p>}
              </div>
            </div>
          )}

          {data.contacts.length > 0 && (
            <div className="card card-pad">
              <h2 className="font-display text-lg font-semibold">Contacts</h2>
              <ul className="mt-3 space-y-3">
                {data.contacts.map((c) => (
                  <li key={c.id} className="flex items-center gap-3 text-sm">
                    <span className="flex h-8 w-8 items-center justify-center rounded-full bg-ink-800"><UserRound className="h-4 w-4 text-mist-400" /></span>
                    <div><div className="font-medium">{c.name}</div><div className="text-xs text-mist-500">{c.role}</div></div>
                  </li>
                ))}
              </ul>
              <p className="mt-3 text-[11px] text-mist-500">Synthetic contacts for demonstration.</p>
            </div>
          )}
        </div>
      </div>

      <div className="mt-4 grid gap-4 lg:grid-cols-2">
        <div className="card card-pad">
          <h2 className="font-display text-lg font-semibold">Buying signals</h2>
          <p className="mt-1 text-sm text-mist-400">Kept only when the quoted evidence appears in the source text.</p>
          <div className="mt-4 space-y-3">
            {positives.length ? positives.map((s) => <EvidenceCard key={s.id} signal={s} />)
              : <p className="rounded-xl border border-dashed border-ink-700 p-4 text-sm text-mist-400">No verified buying signals for this account.</p>}
          </div>
          {negatives.length > 0 && (
            <>
              <h3 className="mt-6 text-sm font-semibold text-mist-300">Disqualifiers</h3>
              <div className="mt-3 space-y-3">{negatives.map((s) => <EvidenceCard key={s.id} signal={s} />)}</div>
            </>
          )}
        </div>

        <div className="card card-pad">
          <h2 className="font-display text-lg font-semibold">Activity</h2>
          {data.activities.length ? (
            <ol className="mt-4 space-y-4 border-l border-ink-700 pl-4">
              {data.activities.map((a) => (
                <li key={a.id} className="relative text-sm">
                  <span className="absolute -left-[21px] top-1.5 h-2.5 w-2.5 rounded-full border-2 border-ink-900 bg-signal-500" />
                  <div className="font-medium">{ACTIVITY_LABEL[a.type] ?? a.type.replace(/_/g, " ")}</div>
                  <div className="text-xs text-mist-500">{shortDate(a.timestamp)}</div>
                </li>
              ))}
            </ol>
          ) : <p className="mt-4 text-sm text-mist-400">No activity yet. This account hasn't been worked.</p>}
        </div>
      </div>
    </div>
  );
}

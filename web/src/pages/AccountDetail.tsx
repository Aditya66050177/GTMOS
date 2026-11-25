import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ArrowLeft, Check, Minus } from "lucide-react";
import { api } from "../lib/api";
import { useAsync } from "../lib/useAsync";
import { ActionBadge, ComponentBars, EmptyState, ErrorBox, EvidenceCard, Loading, Panel, ScoreBlock, TierBadge } from "../components/ui";
import { shortDate } from "../lib/format";

const ACTIVITY_LABEL: Record<string, string> = {
  outreach_sent: "Outreach sent", reply_received: "Reply received", meeting_held: "Meeting held",
  opportunity_created: "Opportunity created", deal_won: "Deal won", deal_lost: "Deal lost",
  outreach_approved: "Draft approved", stage_change: "Stage changed", rejected_signal: "Claim rejected",
  research_note: "Research note ingested",
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
  if (error || !data) return <ErrorBox message={error ?? "No data returned."} onRetry={reload} />;
  const { account, score, recommendation: rec } = data;
  const positives = data.signals.filter((s) => !s.negative);
  const negatives = data.signals.filter((s) => s.negative);
  const blocked = rec?.action === "DEPRIORITIZE";
  const pendingDraft = data.drafts.find((d) => d.status === "pending");

  return (
    <div className="space-y-4">
      <Link to="/app/accounts" className="inline-flex items-center gap-1 text-sm text-ink-3 hover:text-ink">
        <ArrowLeft className="h-4 w-4" aria-hidden /> Prioritized accounts
      </Link>

      <section className="panel panel-pad">
        <div className="flex flex-col gap-5 md:flex-row md:items-start">
          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center gap-2">
              <h1 className="h-page">{account.name}</h1>
              <TierBadge tier={account.tier} />
              <ActionBadge action={rec?.action} />
            </div>
            <div className="mt-1 text-ink-3">
              {[account.industry, account.employee_count != null ? `${account.employee_count} employees` : null, account.country, account.funding, account.domain].filter(Boolean).join(" · ")}
            </div>
            {account.description && <p className="mt-3 max-w-2xl text-ink-2">{account.description}</p>}
            {account.technology_stack.length > 0 && (
              <div className="mt-3 flex flex-wrap gap-1">
                {account.technology_stack.map((t) => <span key={t} className="badge border-line bg-subtle font-medium text-ink-2">{t}</span>)}
              </div>
            )}
          </div>
          <div className="flex items-start gap-6 md:border-l md:border-line md:pl-6">
            {score && <ScoreBlock score={score.total} />}
            <dl className="space-y-2 text-sm">
              <div><dt className="label mb-0">Pipeline stage</dt><dd className="font-medium">{account.stage}</dd></div>
              <div><dt className="label mb-0">Intent</dt><dd className="num font-medium">{account.intent_score.toFixed(1)} / 20</dd></div>
            </dl>
          </div>
        </div>
      </section>

      <div className="grid gap-4 lg:grid-cols-[1.15fr_0.85fr]">
        {score && (
          <Panel title="Why this score" action={<span className="text-2xs text-ink-4">Same inputs, same result</span>}>
            <ComponentBars components={score.components} />
            <table className="tbl mt-5">
              <thead><tr><th className="w-6" aria-label="Met" /><th>Rule</th><th className="r">Points</th></tr></thead>
              <tbody>
                {score.reasons.map((r, i) => (
                  <tr key={`${r.rule}-${i}`}>
                    <td>
                      {r.met
                        ? <Check className="h-4 w-4 text-accent-600" aria-label="Met" />
                        : <Minus className="h-4 w-4 text-ink-4" aria-label="Not met" />}
                    </td>
                    <td><span className="font-medium text-ink">{r.rule}</span><div className="text-ink-3">{r.text}</div></td>
                    <td className="r font-medium">{r.points >= 0 ? "+" : ""}{r.points.toFixed(1)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Panel>
        )}

        <div className="space-y-4">
          {rec && (
            <Panel title="Recommended next action" action={<ActionBadge action={rec.action} />}>
              <p className="text-ink-2">{rec.reason}</p>
              <dl className="mt-3 grid grid-cols-2 gap-3 border-t border-line pt-3">
                <div><dt className="label">Persona</dt><dd>{rec.suggested_persona ?? "—"}</dd></div>
                <div><dt className="label">Angle</dt><dd>{rec.suggested_angle ?? "—"}</dd></div>
              </dl>
              <div className="mt-4">
                {pendingDraft ? (
                  <Link to="/app/review" className="btn-primary w-full">Review the pending draft</Link>
                ) : (
                  <button className="btn-primary w-full" disabled={blocked || drafting} onClick={generateDraft}>
                    {drafting ? "Drafting…" : "Draft outreach from evidence"}
                  </button>
                )}
                {blocked && <p className="mt-2 text-xs text-ink-3">Deprioritized accounts can't get outreach drafts. The rule table blocks it, not the model.</p>}
                {draftError && <p className="mt-2 text-xs text-danger-700" role="alert">{draftError}</p>}
              </div>
            </Panel>
          )}

          {data.contacts.length > 0 && (
            <Panel title="Contacts" action={<span className="text-2xs text-ink-4">Fictional</span>} flush>
              <ul className="divide-y divide-line">
                {data.contacts.map((c) => (
                  <li key={c.id} className="px-4 py-2.5 sm:px-5">
                    <div className="font-medium text-ink">{c.name}</div>
                    <div className="text-xs text-ink-3">{c.role}</div>
                  </li>
                ))}
              </ul>
            </Panel>
          )}
        </div>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <Panel title={`Buying signals (${positives.length})`} action={<span className="text-2xs text-ink-4">Kept only if the quote is in the source</span>}>
          <div className="space-y-2.5">
            {positives.length
              ? positives.map((s) => <EvidenceCard key={s.id} signal={s} />)
              : <EmptyState title="No verified buying signals">Nothing in this account's research notes passed the evidence check.</EmptyState>}
          </div>
          {negatives.length > 0 && (
            <div className="mt-5 border-t border-line pt-4">
              <h3 className="eyebrow mb-2">Disqualifiers</h3>
              <div className="space-y-2.5">{negatives.map((s) => <EvidenceCard key={s.id} signal={s} />)}</div>
            </div>
          )}
        </Panel>

        <Panel title="Activity" flush>
          {data.activities.length ? (
            <ol className="divide-y divide-line">
              {data.activities.map((a) => (
                <li key={a.id} className="flex items-baseline justify-between gap-3 px-4 py-2.5 sm:px-5">
                  <span className="text-ink-2">{ACTIVITY_LABEL[a.type] ?? a.type.replace(/_/g, " ")}</span>
                  <span className="num whitespace-nowrap text-xs text-ink-4">{shortDate(a.timestamp)}</span>
                </li>
              ))}
            </ol>
          ) : <div className="panel-pad"><EmptyState title="No activity yet">This account hasn't been worked.</EmptyState></div>}
        </Panel>
      </div>
    </div>
  );
}

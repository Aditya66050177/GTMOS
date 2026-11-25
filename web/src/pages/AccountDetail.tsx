import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ArrowLeft, Check, Minus } from "lucide-react";
import { api, type AccountDetail, type Explanation } from "../lib/api";
import { useAsync } from "../lib/useAsync";
import { ActionBadge, DataTag, EmptyState, ErrorBox, Loading, Panel, TierBadge } from "../components/ui";
import { EvidenceInspector, FIT_MEANING, INTENT_MEANING, RuleExplanation, ScoreTriplet } from "../components/intel";
import { shortDate, signalLabel } from "../lib/format";

const ACTIVITY_LABEL: Record<string, string> = {
  outreach_sent: "Outreach logged as sent", reply_received: "Reply received", meeting_held: "Meeting held",
  opportunity_created: "Opportunity created", deal_won: "Deal won", deal_lost: "Deal lost",
  outreach_approved: "Draft approved", stage_change: "Stage changed", rejected_signal: "Claim rejected",
  research_note: "Research note ingested",
};
const DRAFT_STATUS: Record<string, [string, string]> = {
  pending: ["Awaiting review", "border-warn-200 bg-warn-50 text-warn-700"],
  approved: ["Approved, not sent", "border-accent-100 bg-accent-50 text-accent-700"],
  sent: ["Logged as sent by a person", "border-line-strong bg-surface text-ink-2"],
  rejected: ["Rejected", "border-neutral-200 bg-neutral-100 text-ink-4"],
};

interface Bundle { detail: AccountDetail; explain: Explanation | null }

async function load(id: number): Promise<Bundle> {
  if (!Number.isInteger(id) || id <= 0) throw new Error("That isn't a valid account id.");
  const detail = await api.account(id);
  let explain: Explanation | null = null;
  try { explain = await api.explain(id); } catch { explain = null; }   // unscored accounts have no explanation
  return { detail, explain };
}

function FitBreakdown({ e }: { e: Explanation }) {
  return (
    <div className="space-y-4">
      {e.fit.components.map((c) => (
        <div key={c.name}>
          <div className="mb-1 flex items-baseline justify-between gap-3">
            <span className="font-medium text-ink">{c.name}</span>
            <span className="num">{c.score.toFixed(1)}<span className="text-ink-4"> / {c.max_score}</span></span>
          </div>
          <div className="h-1.5 rounded-full bg-neutral-200" aria-hidden><div className="h-1.5 rounded-full bg-accent-600" style={{ width: `${(c.score / c.max_score) * 100}%` }} /></div>
          <ul className="mt-1.5 space-y-1">
            {c.reasons.map((r, i) => (
              <li key={i} className="flex gap-2 text-xs">
                {r.met ? <Check className="mt-0.5 h-3.5 w-3.5 shrink-0 text-accent-600" aria-label="Met" /> : <Minus className="mt-0.5 h-3.5 w-3.5 shrink-0 text-ink-4" aria-label="Not met" />}
                <span className="flex-1 text-ink-2">{r.text}</span>
                <span className={`num whitespace-nowrap ${r.points < 0 ? "text-danger-700" : "text-ink-3"}`}>{r.points >= 0 ? "+" : ""}{r.points.toFixed(1)}</span>
              </li>
            ))}
          </ul>
        </div>
      ))}
    </div>
  );
}

export default function AccountDetailPage() {
  const id = Number(useParams().id);
  const { data, error, loading, reload } = useAsync(() => load(id), [id]);
  const [drafting, setDrafting] = useState(false);
  const [draftError, setDraftError] = useState<string | null>(null);

  async function generateDraft() {
    setDrafting(true);
    setDraftError(null);
    try { await api.personalize(id); await reload(); }
    catch (e) { setDraftError(e instanceof Error ? e.message : String(e)); }
    finally { setDrafting(false); }
  }

  if (loading && !data) return <Loading label="Loading account intelligence" />;
  if (error || !data) return <ErrorBox message={error ?? "No data returned."} onRetry={reload} />;
  const { detail, explain: e } = data;
  const account = detail.account;
  const rec = e?.recommendation;
  const blocked = rec?.action === "DEPRIORITIZE";
  const pendingDraft = detail.drafts.find((d) => d.status === "pending");

  return (
    <div className="space-y-4">
      <Link to="/app/accounts" className="inline-flex items-center gap-1 text-sm text-ink-3 hover:text-ink">
        <ArrowLeft className="h-4 w-4" aria-hidden /> Prioritized accounts
      </Link>

      <header className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <h1 className="h-page">{account.name}</h1>
            {e && <TierBadge tier={e.total.tier} />}
            {rec && <ActionBadge action={rec.action} />}
            {e?.includes_synthetic_demo_additions && <DataTag>Includes a synthetic demo note</DataTag>}
          </div>
          <div className="mt-1 text-ink-3">
            {[account.industry, account.employee_count != null ? `${account.employee_count} employees` : null, account.country, account.funding, account.domain].filter(Boolean).join(" · ")}
          </div>
          {account.description && <p className="mt-2 max-w-3xl text-ink-2">{account.description}</p>}
        </div>
        <div className="text-xs text-ink-3 sm:text-right">
          <div>Stage: <span className="font-medium text-ink">{account.stage}</span> <span className="text-ink-4">(simulated pipeline)</span></div>
          {account.technology_stack.length > 0 && <div className="mt-1">Runs {account.technology_stack.join(", ")}</div>}
        </div>
      </header>

      {!e ? (
        <EmptyState title="This account has no score yet">There is no fit, intent or recommendation to explain until the account is scored.</EmptyState>
      ) : (
        <>
          <div className="grid gap-4 lg:grid-cols-[1.05fr_0.95fr]">
            <div className="space-y-2">
              <ScoreTriplet fit={e.fit.score} intent={e.intent.score} total={e.total.total} tier={e.total.tier} />
              <p className="text-2xs text-ink-4 sm:hidden"><b>Fit</b>: {FIT_MEANING} <b>Intent</b>: {INTENT_MEANING}</p>
            </div>
            <Panel title="Recommended next action" action={<ActionBadge action={rec!.action} />}>
              <RuleExplanation e={e} />
              <div className="mt-4 border-t border-line pt-3">
                {pendingDraft ? (
                  <a href="#outreach" className="btn-primary w-full">Review the pending draft below</a>
                ) : (
                  <button className="btn-primary w-full" disabled={blocked || drafting} onClick={generateDraft}>
                    {drafting ? "Drafting…" : "Draft outreach from this evidence"}
                  </button>
                )}
                {blocked && <p className="mt-2 text-xs text-ink-3">Deprioritized accounts can't get outreach drafts. The rule table blocks it, not the model.</p>}
                {draftError && <p className="mt-2 text-xs text-danger-700" role="alert">{draftError}</p>}
              </div>
            </Panel>
          </div>

          <div className="grid gap-4 lg:grid-cols-[0.8fr_1.2fr]">
            <Panel title={`Why the fit is ${e.fit.score.toFixed(1)} / 80`}>
              <p className="mb-4 text-xs text-ink-3">{FIT_MEANING} Computed by fixed rules: the same inputs always give the same result.</p>
              <FitBreakdown e={e} />
            </Panel>
            <section id="evidence" className="scroll-mt-20">
            <Panel title={`Why the intent is ${e.intent.score.toFixed(1)} / 20: evidence inspector`}>
              <p className="mb-3 text-xs text-ink-3">{INTENT_MEANING} Each signal's sentence is quoted exactly from the stored research note.</p>
              <EvidenceInspector e={e} />
            </Panel>
            </section>
          </div>
        </>
      )}

      <div className="grid gap-4 lg:grid-cols-[1.2fr_0.8fr]">
        <section id="outreach" className="scroll-mt-20">
          <Panel title="Outreach for this account" action={<Link to="/app/review" className="text-sm font-medium text-accent-700 hover:underline">Review queue</Link>} flush>
            {detail.drafts.length ? (
              <ul className="divide-y divide-line">
                {detail.drafts.map((d) => {
                  const [label, style] = DRAFT_STATUS[d.status] ?? [d.status, ""];
                  return (
                    <li key={d.id} className="px-4 py-3.5 sm:px-5">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className={`badge ${style}`}>{label}</span>
                        {d.edited && <span className="badge border-line-strong bg-surface text-ink-3">edited by reviewer</span>}
                        <span className="text-2xs text-ink-4">Drafted {shortDate(d.created_at)}</span>
                      </div>
                      <pre className="mt-2 line-clamp-4 whitespace-pre-wrap font-sans text-sm text-ink-2">{d.body}</pre>
                      <div className="mt-2 text-xs text-ink-3">
                        <span className="font-medium">Based on:</span>{" "}
                        {d.evidence.length ? d.evidence.map((ev) => `${signalLabel(ev.type)} (${ev.source})`).join(", ") : "profile facts only"}
                      </div>
                      {d.status === "pending" && <Link to="/app/review" className="mt-2 inline-block text-sm font-medium text-accent-700 hover:underline">Approve, edit or reject in the review queue</Link>}
                    </li>
                  );
                })}
              </ul>
            ) : (
              <div className="panel-pad"><EmptyState title="No drafts for this account">{blocked ? "The rule table blocks drafts for deprioritized accounts." : "Draft one from the recommended-action panel."}</EmptyState></div>
            )}
          </Panel>
        </section>

        <div className="space-y-4">
          {detail.contacts.length > 0 && (
            <Panel title="Contacts" action={<span className="text-2xs text-ink-4">Fictional</span>} flush>
              <ul className="divide-y divide-line">
                {detail.contacts.map((c) => (
                  <li key={c.id} className="px-4 py-2.5 sm:px-5"><div className="font-medium text-ink">{c.name}</div><div className="text-xs text-ink-3">{c.role}</div></li>
                ))}
              </ul>
            </Panel>
          )}
          {e && e.research_notes.length > 0 && (
            <Panel title="Research notes (provenance)" flush>
              <ul className="divide-y divide-line">
                {e.research_notes.map((n, i) => (
                  <li key={i} className="px-4 py-2.5 sm:px-5">
                    <div className="flex flex-wrap items-center gap-2 text-2xs text-ink-4">
                      <span>{n.source} · {shortDate(n.date)}</span>
                      {n.dataset === "demo_addition" && <span className="badge border-warn-200 bg-warn-50 text-warn-700">synthetic demo addition</span>}
                      <span>{n.signals_extracted} signal{n.signals_extracted === 1 ? "" : "s"} extracted</span>
                    </div>
                    <p className="mt-1 text-xs text-ink-2">{n.raw_text}</p>
                  </li>
                ))}
              </ul>
            </Panel>
          )}
          <Panel title="Activity" flush>
            {detail.activities.length ? (
              <ol className="max-h-72 divide-y divide-line overflow-y-auto">
                {detail.activities.map((a) => (
                  <li key={a.id} className="flex items-baseline justify-between gap-3 px-4 py-2 sm:px-5">
                    <span className="text-ink-2">{ACTIVITY_LABEL[a.type] ?? a.type.replace(/_/g, " ")}</span>
                    <span className="num whitespace-nowrap text-xs text-ink-4">{shortDate(a.timestamp)}</span>
                  </li>
                ))}
              </ol>
            ) : <div className="panel-pad"><EmptyState title="No activity yet" /></div>}
          </Panel>
        </div>
      </div>
    </div>
  );
}

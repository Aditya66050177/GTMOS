import { useState } from "react";
import { Link } from "react-router-dom";
import { CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Send } from "lucide-react";
import { api, type AskResponse, type ExecutiveAnswer } from "../lib/api";
import { useAsync } from "../lib/useAsync";
import { ActionBadge, DataTag, ErrorBox, Kpi, Loading, PageHeader, Panel, TierBadge } from "../components/ui";

const SUGGESTIONS = [
  "How is the funnel doing?",
  "Where do we drop off between stages?",
  "Which tier converts best?",
  "Which industries reply most?",
  "Which outreach angle works best?",
];

// Categorical slots 1-4 of the validated reference palette (CVD-separated; see T3 report).
// Three sit below 3:1 on white, so the chart also offers a table view.
const SERIES = [
  { key: "contacted", color: "#257de0", name: "Contacted" },
  { key: "replies", color: "#f47230", name: "Replies" },
  { key: "meetings", color: "#00b894", name: "Meetings" },
  { key: "won", color: "#f2a600", name: "Won" },
] as const;

const AXIS = { fill: "#667085", fontSize: 11 };

const QUESTIONS: { id: string; label: string }[] = [
  { id: "worth-pursuing", label: "Which accounts are worth pursuing?" },
  { id: "nurture", label: "Which accounts should we nurture?" },
  { id: "stuck", label: "Where are opportunities getting stuck?" },
  { id: "signals-by-tier", label: "Which buying signals appear across priority tiers?" },
  { id: "investigate-next", label: "Which accounts should we investigate next?" },
];

function Answer({ a }: { a: ExecutiveAnswer }) {
  return (
    <div className="space-y-4">
      <p className="text-base font-medium text-ink">{a.summary}</p>
      <div className="grid gap-4 lg:grid-cols-2">
        <div>
          <h3 className="eyebrow">Observations · from database values</h3>
          <ul className="mt-1.5 space-y-1.5">
            {a.observations.map((o, i) => <li key={i} className="border-l-[3px] border-accent-600 pl-3 text-ink-2">{o.text}</li>)}
          </ul>
        </div>
        <div>
          <h3 className="eyebrow">Hypotheses · not established by the data</h3>
          {a.hypotheses.length ? (
            <ul className="mt-1.5 space-y-1.5">
              {a.hypotheses.map((h, i) => (
                <li key={i} className="border-l-[3px] border-warn-200 pl-3 text-ink-2">
                  <span className="badge mr-1.5 border-warn-200 bg-warn-50 text-warn-700">Hypothesis</span>{h.text}
                </li>
              ))}
            </ul>
          ) : <p className="mt-1.5 text-ink-3">None offered for this answer.</p>}
        </div>
      </div>
      {a.accounts.length > 0 && (
        <div className="overflow-x-auto rounded-md border border-line" tabIndex={0}>
          <table className="tbl">
            <thead><tr><th>Account</th><th>Tier</th><th>Action</th><th className="r">Fit</th><th className="r">Intent</th><th>Why listed</th></tr></thead>
            <tbody>
              {a.accounts.slice(0, 10).map((r) => (
                <tr key={r.id}>
                  <td>
                    <Link to={`/app/accounts/${r.id}#evidence`} className="font-medium text-ink hover:text-accent-700 hover:underline">{r.name}</Link>
                    {r.uses_synthetic_demo_additions && <span className="badge ml-1.5 border-line-strong bg-subtle text-ink-3">demo note</span>}
                  </td>
                  <td>{r.tier ? <TierBadge tier={r.tier} /> : "—"}</td>
                  <td><ActionBadge action={r.action} /></td>
                  <td className="r">{r.fit?.toFixed(1) ?? "—"}</td>
                  <td className="r">{r.intent?.toFixed(1) ?? "—"}</td>
                  <td className="text-xs text-ink-3">{r.why.join(" · ")}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {a.accounts.length > 10 && <p className="px-3 py-2 text-2xs text-ink-4">Showing 10 of {a.accounts.length}.</p>}
        </div>
      )}
      <details className="text-xs text-ink-3">
        <summary className="cursor-pointer font-medium hover:text-ink">Data sources, provenance and selection rules</summary>
        <div className="mt-2 grid gap-3 lg:grid-cols-2">
          <ul className="list-disc space-y-0.5 pl-4">{Object.values(a.data_provenance).map((v) => <li key={v}>{v}</li>)}</ul>
          <ul className="list-disc space-y-0.5 pl-4">{a.selection_rules.map((v) => <li key={v}>{v}</li>)}{a.data_sources.map((v) => <li key={v}>Source: {v}</li>)}</ul>
        </div>
        {a.data_quality.length > 0 && <div className="mt-2"><span className="font-medium">Data quality:</span> {a.data_quality.join(" ")}</div>}
        <div className="mt-2">{a.generated_by}</div>
      </details>
    </div>
  );
}

function ExecutiveQuestions() {
  const [active, setActive] = useState<string | null>(null);
  const [answer, setAnswer] = useState<ExecutiveAnswer | null>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  async function open(id: string) {
    setActive(id); setBusy(true); setErr(null);
    try { setAnswer(await api.executive(id)); }
    catch (e) { setErr(e instanceof Error ? e.message : String(e)); setAnswer(null); }
    finally { setBusy(false); }
  }

  return (
    <section id="executive" className="scroll-mt-20">
      <Panel title="Executive questions" action={<span className="text-2xs text-ink-4">Answered by database queries, not a language model</span>}>
        <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-5" role="group" aria-label="Executive questions">
          {QUESTIONS.map((q) => (
            <button key={q.id} type="button" aria-pressed={active === q.id} onClick={() => void open(q.id)}
              className={`rounded-md border px-3 py-2.5 text-left text-sm font-medium transition-colors ${active === q.id ? "border-accent-600 bg-accent-50 text-accent-700" : "border-line-strong bg-surface text-ink-2 hover:border-accent-600"}`}>
              {q.label}
            </button>
          ))}
        </div>
        <div className="mt-4" aria-live="polite">
          {busy && <p className="text-ink-3" role="status">Running the query…</p>}
          {err && <p className="text-danger-700" role="alert">{err}</p>}
          {!busy && answer && <Answer a={answer} />}
          {!busy && !answer && !err && <p className="text-ink-3">Choose a question to see what the data shows and what it does not.</p>}
        </div>
      </Panel>
    </section>
  );
}


function Analyst() {
  const [q, setQ] = useState("");
  const [busy, setBusy] = useState(false);
  const [answer, setAnswer] = useState<AskResponse | null>(null);
  const [err, setErr] = useState<string | null>(null);

  async function ask(question: string) {
    if (!question.trim()) return;
    setQ(question); setBusy(true); setErr(null);
    try { setAnswer(await api.ask(question)); }
    catch (e) { setErr(e instanceof Error ? e.message : String(e)); }
    finally { setBusy(false); }
  }

  return (
    <Panel title="Ask the analyst" action={<span className="text-2xs text-ink-4">Predefined queries only</span>}>
      <p className="text-ink-3">The model only picks which predefined query to run. Every number comes from SQL and pandas.</p>
      <form className="mt-3 flex gap-2" onSubmit={(e) => { e.preventDefault(); void ask(q); }}>
        <label className="sr-only" htmlFor="ask">Question</label>
        <input id="ask" className="input" placeholder="Ask about the funnel…" value={q} onChange={(e) => setQ(e.target.value)} maxLength={200} />
        <button className="btn-primary px-3" disabled={busy || !q.trim()} aria-label="Ask"><Send className="h-4 w-4" aria-hidden /></button>
      </form>
      <div className="mt-2.5 flex flex-wrap gap-1.5">
        {SUGGESTIONS.map((s) => (
          <button key={s} type="button" className="badge border-line-strong bg-surface py-1 font-medium text-ink-2 hover:border-accent-600 hover:text-accent-700" onClick={() => void ask(s)}>{s}</button>
        ))}
      </div>
      {busy && <p className="mt-3 text-ink-3" role="status">Running query…</p>}
      {err && <p className="mt-3 text-danger-700" role="alert">{err}</p>}
      {answer && !busy && (
        <div className="mt-4 rounded-md border border-line bg-subtle p-3.5">
          <div className="font-mono text-2xs text-ink-4">ran {answer.function_called}()</div>
          <p className="mt-1.5 leading-relaxed text-ink">{answer.explanation}</p>
          {!!answer.observations?.length && (
            <div className="mt-2"><div className="eyebrow">Observations</div><ul className="mt-1 list-disc space-y-0.5 pl-4 text-ink-2">{answer.observations.map((o, i) => <li key={i}>{o}</li>)}</ul></div>
          )}
          {!!answer.hypotheses?.length && (
            <div className="mt-2"><div className="eyebrow">Hypotheses · not established by the data</div><ul className="mt-1 list-disc space-y-0.5 pl-4 text-ink-2">{answer.hypotheses.map((h, i) => <li key={i}>{h}</li>)}</ul></div>
          )}
          {answer.data_label && <p className="mt-2 text-2xs text-ink-4">{answer.data_label}</p>}
          <details className="mt-2 text-xs text-ink-3">
            <summary className="cursor-pointer font-medium hover:text-ink">Show the data it used</summary>
            <pre className="mt-2 max-h-64 overflow-auto rounded border border-line bg-surface p-3 font-mono text-[11px] leading-relaxed text-ink-2">{JSON.stringify(answer.data, null, 2)}</pre>
          </details>
        </div>
      )}
    </Panel>
  );
}

export default function AnalyticsPage() {
  const funnel = useAsync(api.funnel);
  const trends = useAsync(api.trends);
  const [view, setView] = useState<"chart" | "table">("chart");
  if ((funnel.loading && !funnel.data) || (trends.loading && !trends.data)) return <Loading />;
  if (funnel.error || !funnel.data) return <ErrorBox message={funnel.error ?? "No data returned."} onRetry={funnel.reload} />;
  const t = funnel.data.totals;
  const weeks = trends.data?.weekly_trends ?? [];
  const tiers = funnel.data.performance_by_tier as { tier: string; accounts: number; contacted: number; replies: number; meetings: number; won: number; win_rate_pct: number }[];
  const industries = (funnel.data.performance_by_industry as { industry: string; accounts: number; contacted: number; replies: number; meetings: number; won: number }[]).slice(0, 8);

  return (
    <div className="space-y-4">
      <PageHeader eyebrow="Funnel analytics" title="Analytics"
        description="Pipeline numbers on this page come from a seeded 40-day simulation on synthetic accounts. They are not real sales outcomes.">
        <DataTag>Simulated pipeline</DataTag>
      </PageHeader>

      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <Kpi value={t.contacted} label="Contacted" hint={`of ${t.total_accounts} accounts`} />
        <Kpi value={t.replies} label="Replies" />
        <Kpi value={t.meetings} label="Meetings" />
        <Kpi value={t.won} label="Won" hint={`${t.lost} lost`} />
      </div>

      <ExecutiveQuestions />

      <div className="grid gap-4 lg:grid-cols-[1.25fr_0.75fr]">
        <Panel title="Weekly activity" action={
          <div className="segmented" role="group" aria-label="Weekly activity view">
            <button type="button" aria-pressed={view === "chart"} onClick={() => setView("chart")}>Chart</button>
            <button type="button" aria-pressed={view === "table"} onClick={() => setView("table")}>Table</button>
          </div>
        }>
          {view === "chart" ? (
            <div className="h-72" role="img" aria-label="Weekly contacted, replies, meetings and won counts. Use the Table view for exact values.">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={weeks} margin={{ left: -20, right: 8, top: 8, bottom: 0 }}>
                  <CartesianGrid stroke="#EAECF0" vertical={false} />
                  <XAxis dataKey="week" tick={AXIS} tickLine={false} axisLine={{ stroke: "#D0D5DD" }} tickFormatter={(w: string) => w.split("-")[1] ?? w} />
                  <YAxis tick={AXIS} tickLine={false} axisLine={false} allowDecimals={false} />
                  <Tooltip
                    contentStyle={{ background: "#FFFFFF", border: "1px solid #D0D5DD", borderRadius: 6, fontSize: 12, color: "#101828" }}
                    labelStyle={{ color: "#344054", fontWeight: 600 }} itemStyle={{ color: "#344054" }}
                    cursor={{ stroke: "#98A2B3", strokeDasharray: "3 3" }}
                  />
                  <Legend iconType="plainline" wrapperStyle={{ fontSize: 12, color: "#475467" }} />
                  {SERIES.map((s) => (
                    <Line key={s.key} type="monotone" dataKey={s.key} name={s.name} stroke={s.color} strokeWidth={2}
                      dot={false} activeDot={{ r: 4, stroke: "#FFFFFF", strokeWidth: 2 }} />
                  ))}
                </LineChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <div className="max-h-72 overflow-auto rounded-md border border-line" tabIndex={0}>
              <table className="tbl">
                <thead><tr><th>Week</th>{SERIES.map((s) => <th key={s.key} className="r">{s.name}</th>)}</tr></thead>
                <tbody>
                  {weeks.map((w) => (
                    <tr key={w.week}><td>{w.week}</td>{SERIES.map((s) => <td key={s.key} className="r">{w[s.key]}</td>)}</tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Panel>

        <Panel title="Stage conversion">
          <ul className="space-y-3.5">
            {funnel.data.conversions.map((c) => (
              <li key={c.from_stage}>
                <div className="mb-1 flex justify-between gap-2">
                  <span className="text-ink-2">{c.from_stage} → {c.to_stage}</span>
                  <span className="num font-medium">{c.conversion_rate_pct}%</span>
                </div>
                <div className="h-1.5 rounded-full bg-neutral-200" aria-hidden><div className="h-1.5 rounded-full bg-accent-600" style={{ width: `${c.conversion_rate_pct}%` }} /></div>
                <div className="num mt-1 text-2xs text-ink-4">{c.to_count} of {c.from_count}</div>
              </li>
            ))}
          </ul>
        </Panel>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <Analyst />
        <div className="space-y-4">
          <Panel title="By fit tier" flush>
            <div className="overflow-x-auto" tabIndex={0}>
              <table className="tbl">
                <thead><tr><th>Tier</th><th className="r">Accounts</th><th className="r">Contacted</th><th className="r">Replies</th><th className="r">Win rate</th></tr></thead>
                <tbody>
                  {tiers.map((r) => (
                    <tr key={r.tier}><td className="font-medium">{r.tier}</td><td className="r">{r.accounts}</td><td className="r">{r.contacted}</td><td className="r">{r.replies}</td><td className="r">{r.win_rate_pct}%</td></tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Panel>
          <Panel title="By industry" flush>
            <div className="overflow-x-auto" tabIndex={0}>
              <table className="tbl">
                <thead><tr><th>Industry</th><th className="r">Contacted</th><th className="r">Replies</th><th className="r">Meetings</th><th className="r">Won</th></tr></thead>
                <tbody>
                  {industries.map((r) => (
                    <tr key={r.industry}><td className="font-medium">{r.industry}</td><td className="r">{r.contacted}</td><td className="r">{r.replies}</td><td className="r">{r.meetings}</td><td className="r">{r.won}</td></tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Panel>
        </div>
      </div>
    </div>
  );
}

import { useState } from "react";
import { CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Send, Sparkles } from "lucide-react";
import { api, type AskResponse } from "../lib/api";
import { useAsync } from "../lib/useAsync";
import { ErrorBox, Loading, PageHeader, Stat } from "../components/ui";

const SUGGESTIONS = [
  "How is the funnel doing?",
  "Where do we drop off between stages?",
  "Which tier converts best?",
  "Which industries reply most?",
  "Which outreach angle works best?",
];

const SERIES = [
  { key: "contacted", color: "#5CC8FF", name: "Contacted" },
  { key: "replies", color: "#4DFFAE", name: "Replies" },
  { key: "meetings", color: "#FFC857", name: "Meetings" },
  { key: "won", color: "#FF6B81", name: "Won" },
];

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
    <div className="card card-pad">
      <div className="flex items-center gap-2">
        <Sparkles className="h-5 w-5 text-signal-400" />
        <h2 className="font-display text-lg font-semibold">Ask the analyst</h2>
      </div>
      <p className="mt-1 text-sm text-mist-400">
        The model only picks which predefined query to run and phrases the answer. Every number comes from SQL and pandas.
      </p>
      <form className="mt-4 flex gap-2" onSubmit={(e) => { e.preventDefault(); void ask(q); }}>
        <label className="sr-only" htmlFor="ask">Question</label>
        <input id="ask" className="input" placeholder="Ask about the funnel…" value={q} onChange={(e) => setQ(e.target.value)} maxLength={200} />
        <button className="btn-primary" disabled={busy || !q.trim()} aria-label="Ask"><Send className="h-4 w-4" /></button>
      </form>
      <div className="mt-3 flex flex-wrap gap-2">
        {SUGGESTIONS.map((s) => (
          <button key={s} className="chip border-ink-600 bg-ink-850 text-mist-300 hover:border-mist-500" onClick={() => void ask(s)}>{s}</button>
        ))}
      </div>
      {busy && <p className="mt-4 text-sm text-mist-400">Thinking…</p>}
      {err && <p className="mt-4 text-sm text-rose-400">{err}</p>}
      {answer && !busy && (
        <div className="mt-5 rounded-xl border border-ink-700 bg-ink-850 p-4">
          <div className="font-mono text-[11px] text-mist-500">ran: {answer.function_called}()</div>
          <p className="mt-2 text-sm leading-relaxed text-mist-100">{answer.explanation}</p>
          <details className="mt-3 text-xs text-mist-400">
            <summary className="cursor-pointer hover:text-mist-100">Show the data it used</summary>
            <pre className="mt-2 max-h-64 overflow-auto rounded-lg bg-ink-950 p-3 font-mono text-[11px] leading-relaxed">{JSON.stringify(answer.data, null, 2)}</pre>
          </details>
        </div>
      )}
    </div>
  );
}

export default function AnalyticsPage() {
  const funnel = useAsync(api.funnel);
  const trends = useAsync(api.trends);
  if ((funnel.loading && !funnel.data) || (trends.loading && !trends.data)) return <Loading />;
  if (funnel.error || !funnel.data) return <ErrorBox message={funnel.error ?? "No data"} onRetry={funnel.reload} />;
  const t = funnel.data.totals;
  const tiers = funnel.data.performance_by_tier as { tier: string; accounts: number; contacted: number; replies: number; meetings: number; won: number; win_rate_pct: number }[];
  const industries = (funnel.data.performance_by_industry as { industry: string; accounts: number; contacted: number; replies: number; meetings: number; won: number }[]).slice(0, 8);

  return (
    <div>
      <PageHeader eyebrow="Funnel analytics" title="Analytics" />
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <Stat value={t.contacted} label="Contacted" />
        <Stat value={t.replies} label="Replies" />
        <Stat value={t.meetings} label="Meetings" />
        <Stat value={t.won} label="Won" hint={`${t.lost} lost`} />
      </div>

      <div className="mt-4 grid gap-4 lg:grid-cols-[1.2fr_0.8fr]">
        <div className="card card-pad">
          <h2 className="font-display text-lg font-semibold">Weekly activity</h2>
          <div className="mt-4 h-72">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={trends.data?.weekly_trends ?? []} margin={{ left: -18, right: 8, top: 8 }}>
                <CartesianGrid stroke="#222836" vertical={false} />
                <XAxis dataKey="week" tick={{ fill: "#6E788C", fontSize: 11 }} tickLine={false} axisLine={{ stroke: "#2E3546" }} tickFormatter={(w: string) => w.split("-")[1] ?? w} />
                <YAxis tick={{ fill: "#6E788C", fontSize: 11 }} tickLine={false} axisLine={false} allowDecimals={false} />
                <Tooltip contentStyle={{ background: "#11141B", border: "1px solid #2E3546", borderRadius: 12, fontSize: 12 }} labelStyle={{ color: "#C3C9D6" }} />
                <Legend wrapperStyle={{ fontSize: 12, color: "#9AA3B5" }} />
                {SERIES.map((s) => <Line key={s.key} type="monotone" dataKey={s.key} name={s.name} stroke={s.color} strokeWidth={2} dot={false} />)}
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
        <div className="card card-pad">
          <h2 className="font-display text-lg font-semibold">Stage conversion</h2>
          <ul className="mt-4 space-y-4">
            {funnel.data.conversions.map((c) => (
              <li key={c.from_stage}>
                <div className="mb-1 flex justify-between text-sm">
                  <span className="text-mist-300">{c.from_stage} → {c.to_stage}</span>
                  <span className="font-mono tabular-nums">{c.conversion_rate_pct}%</span>
                </div>
                <div className="h-2 rounded-full bg-ink-800"><div className="h-2 rounded-full bg-signal-500" style={{ width: `${c.conversion_rate_pct}%` }} /></div>
                <div className="mt-1 font-mono text-[11px] text-mist-500">{c.to_count} of {c.from_count}</div>
              </li>
            ))}
          </ul>
        </div>
      </div>

      <div className="mt-4 grid gap-4 lg:grid-cols-2">
        <Analyst />
        <div className="space-y-4">
          <div className="card overflow-x-auto">
            <table className="w-full text-sm">
              <caption className="px-5 pt-5 text-left font-display text-lg font-semibold">By fit tier</caption>
              <thead className="text-left text-xs text-mist-500">
                <tr><th className="px-5 py-3 font-medium">Tier</th><th className="px-3 py-3 text-right font-medium">Accts</th><th className="px-3 py-3 text-right font-medium">Contacted</th><th className="px-3 py-3 text-right font-medium">Replies</th><th className="px-5 py-3 text-right font-medium">Win rate</th></tr>
              </thead>
              <tbody className="divide-y divide-ink-800 font-mono tabular-nums">
                {tiers.map((r) => (
                  <tr key={r.tier}><td className="px-5 py-2.5 font-sans">{r.tier}</td><td className="px-3 text-right">{r.accounts}</td><td className="px-3 text-right">{r.contacted}</td><td className="px-3 text-right">{r.replies}</td><td className="px-5 text-right">{r.win_rate_pct}%</td></tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="card overflow-x-auto">
            <table className="w-full text-sm">
              <caption className="px-5 pt-5 text-left font-display text-lg font-semibold">By industry</caption>
              <thead className="text-left text-xs text-mist-500">
                <tr><th className="px-5 py-3 font-medium">Industry</th><th className="px-3 py-3 text-right font-medium">Contacted</th><th className="px-3 py-3 text-right font-medium">Replies</th><th className="px-3 py-3 text-right font-medium">Meetings</th><th className="px-5 py-3 text-right font-medium">Won</th></tr>
              </thead>
              <tbody className="divide-y divide-ink-800 font-mono tabular-nums">
                {industries.map((r) => (
                  <tr key={r.industry}><td className="px-5 py-2.5 font-sans">{r.industry}</td><td className="px-3 text-right">{r.contacted}</td><td className="px-3 text-right">{r.replies}</td><td className="px-3 text-right">{r.meetings}</td><td className="px-5 text-right">{r.won}</td></tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}

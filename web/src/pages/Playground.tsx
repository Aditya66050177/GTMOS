import { useState } from "react";
import { FlaskConical, RotateCcw } from "lucide-react";
import { api, type PlaygroundInput, type PlaygroundResult } from "../lib/api";
import { ActionBadge, ComponentBars, EvidenceCard, PageHeader, ScoreRing, TierBadge } from "../components/ui";

const PRESETS: { label: string; input: PlaygroundInput }[] = [
  {
    label: "Hot SaaS account",
    input: {
      name: "Northwind Cloud", industry: "B2B SaaS", employee_count: 220, country: "US",
      description: "Workflow SaaS with high support ticket volume and high support costs.",
      technology_stack: ["Zendesk", "Salesforce", "Jira"],
      research_note: "Northwind Cloud raised a $40M Series B funding round to scale their platform. They are hiring 25 new support agents to handle a growing customer base.",
    },
  },
  {
    label: "Rumour, not a signal",
    input: {
      name: "Orbit Analytics", industry: "Software", employee_count: 180, country: "Canada",
      description: "Analytics software with a small, stable help desk.",
      technology_stack: ["Intercom"],
      research_note: "Rumors suggested Orbit was hiring for its support team, but leadership confirmed a hiring freeze. They are not hiring this quarter.",
    },
  },
  {
    label: "Wrong fit",
    input: {
      name: "Corner Bakery Co", industry: "Retail", employee_count: 25, country: "Brazil",
      description: "B2C only neighbourhood bakery.",
      technology_stack: [], research_note: "Corner Bakery Co launched a new seasonal menu.",
    },
  },
];

export default function PlaygroundPage() {
  const [form, setForm] = useState<PlaygroundInput>(PRESETS[0].input);
  const [tech, setTech] = useState(PRESETS[0].input.technology_stack.join(", "));
  const [result, setResult] = useState<PlaygroundResult | null>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  function load(p: PlaygroundInput) { setForm(p); setTech(p.technology_stack.join(", ")); setResult(null); }
  const set = <K extends keyof PlaygroundInput>(k: K, v: PlaygroundInput[K]) => setForm((f) => ({ ...f, [k]: v }));

  async function run(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true); setErr(null);
    try {
      setResult(await api.playground({ ...form, technology_stack: tech.split(",").map((t) => t.trim()).filter(Boolean) }));
    } catch (e2) { setErr(e2 instanceof Error ? e2.message : String(e2)); }
    finally { setBusy(false); }
  }

  return (
    <div>
      <PageHeader eyebrow="Try it" title="Scoring playground" />
      <p className="-mt-3 mb-6 max-w-3xl text-sm text-mist-400">
        Describe any company and paste a research note. GTMOS runs the same signal extractor, 100-point scorer and rule
        table as the rest of the app, against the demo ICP. Nothing you enter is saved.
      </p>

      <div className="grid gap-4 lg:grid-cols-[0.9fr_1.1fr]">
        <form onSubmit={run} className="card card-pad space-y-4">
          <div className="flex flex-wrap gap-2">
            {PRESETS.map((p) => (
              <button type="button" key={p.label} onClick={() => load(p.input)} className="chip border-ink-600 bg-ink-850 text-mist-300 hover:border-mist-500">{p.label}</button>
            ))}
          </div>
          <div className="grid gap-4 sm:grid-cols-2">
            <div><label className="label" htmlFor="pg-name">Company</label><input id="pg-name" className="input" value={form.name} maxLength={80} onChange={(e) => set("name", e.target.value)} /></div>
            <div><label className="label" htmlFor="pg-ind">Industry</label><input id="pg-ind" className="input" required value={form.industry} maxLength={60} onChange={(e) => set("industry", e.target.value)} /></div>
            <div><label className="label" htmlFor="pg-emp">Employees</label><input id="pg-emp" className="input" type="number" min={1} max={1000000} required value={form.employee_count} onChange={(e) => set("employee_count", Number(e.target.value))} /></div>
            <div><label className="label" htmlFor="pg-geo">Country</label><input id="pg-geo" className="input" required value={form.country} maxLength={60} onChange={(e) => set("country", e.target.value)} /></div>
          </div>
          <div><label className="label" htmlFor="pg-desc">What they do and their pain points</label><input id="pg-desc" className="input" value={form.description} maxLength={300} onChange={(e) => set("description", e.target.value)} placeholder="High support ticket volume, slow response time…" /></div>
          <div><label className="label" htmlFor="pg-tech">Tech stack (comma separated)</label><input id="pg-tech" className="input" value={tech} onChange={(e) => setTech(e.target.value)} placeholder="Zendesk, Salesforce" /></div>
          <div>
            <label className="label" htmlFor="pg-note">Research note</label>
            <textarea id="pg-note" className="input min-h-[140px] leading-relaxed" value={form.research_note} maxLength={1200} onChange={(e) => set("research_note", e.target.value)} />
            <div className="mt-1 text-right text-[11px] text-mist-500">{form.research_note.length} / 1200</div>
          </div>
          <button className="btn-primary w-full" disabled={busy}><FlaskConical className="h-4 w-4" /> {busy ? "Scoring…" : "Score this company"}</button>
          {err && <p className="text-sm text-rose-400">{err}</p>}
        </form>

        <div className="space-y-4">
          {!result ? (
            <div className="card card-pad flex min-h-[320px] flex-col items-center justify-center text-center text-sm text-mist-400">
              <FlaskConical className="mb-3 h-8 w-8 text-mist-500" />
              Pick a preset or describe a company, then score it.
            </div>
          ) : (
            <>
              <div className="card card-pad">
                <div className="flex flex-col gap-5 sm:flex-row sm:items-center">
                  <ScoreRing score={result.score.total_score} />
                  <div className="flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <h2 className="font-display text-xl font-semibold">{form.name || "Your company"}</h2>
                      <TierBadge tier={result.score.tier} />
                    </div>
                    <div className="mt-2 flex items-center gap-2 text-sm text-mist-400">Next action <ActionBadge action={result.recommendation.action} /></div>
                    <p className="mt-2 text-sm text-mist-300">{result.recommendation.reason}</p>
                  </div>
                  <button className="btn-ghost self-start px-3" onClick={() => setResult(null)} aria-label="Clear result"><RotateCcw className="h-4 w-4" /></button>
                </div>
                <div className="mt-6"><ComponentBars components={result.score.components} /></div>
              </div>
              <div className="card card-pad">
                <h3 className="font-display text-lg font-semibold">What the extractor found</h3>
                <div className="mt-3 space-y-3">
                  {result.signals.length ? result.signals.map((s, i) => <EvidenceCard key={i} signal={s} />) : (
                    <p className="rounded-xl border border-dashed border-ink-700 p-4 text-sm text-mist-400">
                      {result.note_had_text ? "No verifiable buying signal in that note. Negated, hedged or rumoured claims don't count." : "Add a research note to look for buying signals."}
                    </p>
                  )}
                </div>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

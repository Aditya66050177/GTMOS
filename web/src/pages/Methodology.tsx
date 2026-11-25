import { api, type Methodology, type Overview, type Tier } from "../lib/api";
import { useAsync } from "../lib/useAsync";
import { ActionBadge, DataTag, ErrorBox, Kpi, Loading, PageHeader, Panel, TierBadge } from "../components/ui";
import { FIT_MEANING, INTENT_MEANING, RULE_PLAIN } from "../components/intel";
import { signalLabel } from "../lib/format";

const TIERS: Tier[] = ["Priority 1", "Priority 2", "Priority 3", "Low"];
const pct = (n: number) => `${Math.round(n * 1000) / 10}%`;

const WEAKNESSES = [
  ["Priority 2 is never predicted correctly",
    "On the labelled set, all 19 true Priority 2 accounts come out as Priority 1 (0% recall). The evaluation's proxy intent (support-team size and funding stage) adds enough points to push good-fit accounts over the 90 threshold. The tier cut-offs and the proxy need recalibrating against real outcomes."],
  ["Disqualifiers count twice",
    "Being too small, in the wrong industry or in the wrong country lowers fit and also subtracts from intent. Bad-fit accounts are penalised in both, so the two scores are not independent."],
  ["The offline extractor is rule-based",
    "It rejects negations and rumours, but a sentence with \"reportedly\" or \"may\" that also matches a signal rule is still counted. A live language model would behave differently, and that has not been evaluated."],
  ["The evaluation measures an easier problem than the product faces",
    "Tier accuracy uses the proxy intent, not verified signals. Signal accuracy (100%) uses a simplified keyword matcher on short synthetic sentences, not the production extractor on real research."],
  ["Some rules are debatable",
    "Acme fits the profile closely (69.5 of 80) but, with no intent, lands in Priority 3 and is deprioritized. Arguably the right call is to research it. The rule table is intentionally simple and has not been tuned."],
  ["Everything is synthetic or simulated",
    "Accounts, contacts and research notes are synthetic. The pipeline is a seeded simulation. Nothing here measures real reply rates, conversion or revenue."],
  ["Thresholds are conventions",
    "Signal weights, decay windows (90 and 180 days) and tier cut-offs are reasoned defaults, not values fitted to data."],
] as const;

function Confusion({ m }: { m: Methodology }) {
  const cm = m.evaluation.tier.confusion_matrix;
  return (
    <div className="overflow-x-auto" tabIndex={0}>
      <table className="tbl min-w-[520px]">
        <caption className="sr-only">Confusion matrix: rows are the labelled tier, columns are the predicted tier</caption>
        <thead>
          <tr><th>Labelled \ Predicted</th>{TIERS.map((t) => <th key={t} className="r">{t}</th>)}<th className="r">Recall</th></tr>
        </thead>
        <tbody>
          {TIERS.map((actual) => (
            <tr key={actual}>
              <th scope="row" className="!static !bg-surface !text-left !text-sm !font-medium !normal-case !tracking-normal !text-ink"><TierBadge tier={actual} /></th>
              {TIERS.map((pred) => {
                const n = cm[actual]?.[pred] ?? 0;
                const diag = actual === pred;
                return (
                  <td key={pred} className={`r ${diag ? "bg-accent-50 font-semibold text-accent-700" : n > 0 ? "bg-danger-50 font-semibold text-danger-700" : "text-ink-4"}`}>{n}</td>
                );
              })}
              <td className="r font-semibold">{pct(m.evaluation.tier.recall[actual] ?? 0)}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <p className="mt-2 text-2xs text-ink-4">Shaded teal: correct. Shaded red: wrong tier. Each row is the accounts a person labelled with that tier.</p>
    </div>
  );
}

export default function MethodologyPage() {
  const meth = useAsync(api.methodology);
  const ov = useAsync<Overview>(api.overview);
  if ((meth.loading && !meth.data) || (ov.loading && !ov.data)) return <Loading label="Loading methodology" />;
  if (meth.error || !meth.data) return <ErrorBox message={meth.error ?? "No data returned."} onRetry={meth.reload} />;
  const m = meth.data;
  const icp = ov.data?.icp;
  const ev = m.evaluation;

  return (
    <div className="space-y-4">
      <PageHeader eyebrow="How GTMOS decides" title="Methodology and limitations"
        description="How accounts are scored, how evidence is checked, how the model performs on a labelled set, and where it falls short. Every number on this page is read from the code or computed from the evaluation data.">
        <DataTag>Synthetic evaluation data</DataTag>
      </PageHeader>

      <nav aria-label="On this page" className="flex flex-wrap gap-x-4 gap-y-1 text-xs">
        {[["icp", "ICP"], ["scoring", "Scoring"], ["intent", "Signals and decay"], ["rules", "Recommendation rules"], ["evidence", "Evidence and approval"], ["evaluation", "Evaluation"], ["weaknesses", "Known weaknesses"]].map(([id, label]) => (
          <a key={id} href={`#${id}`} className="font-medium text-accent-700 hover:underline">{label}</a>
        ))}
      </nav>

      <section id="icp" className="scroll-mt-20">
        <Panel title="1. From product description to ideal customer profile">
          <p className="text-ink-2">
            A language model reads the product description and proposes a structured ICP. The output must pass a strict
            schema before any rule uses it. After that, the model has no say in scoring.
          </p>
          {ov.data && <p className="mt-2 text-xs text-ink-3"><span className="font-medium">Product:</span> {ov.data.product.description}</p>}
          {icp ? (
            <dl className="mt-4 grid gap-x-6 gap-y-3 sm:grid-cols-2 lg:grid-cols-3">
              {([
                ["Industries", icp.industries], ["Company size", [`${icp.company_size_min}–${icp.company_size_max} employees`]],
                ["Geographies", icp.geographies], ["Pain points", icp.pain_points], ["Technologies", icp.technologies], ["Exclusions", icp.exclusions],
              ] as [string, string[]][]).map(([label, values]) => (
                <div key={label}>
                  <dt className="label">{label}</dt>
                  <dd className="flex flex-wrap gap-1">{values.map((v) => <span key={v} className="badge border-line bg-subtle font-medium text-ink-2">{v}</span>)}</dd>
                </div>
              ))}
            </dl>
          ) : <p className="mt-3 text-ink-3">The ICP could not be loaded.</p>}
        </Panel>
      </section>

      <section id="scoring" className="scroll-mt-20">
        <Panel title="2. A 100-point score you can audit" flush>
          <div className="panel-pad pb-0">
            <div className="grid gap-3 sm:grid-cols-2">
              <div className="rounded-md border border-line bg-subtle p-3"><div className="font-semibold">Fit: up to {m.fit_max} points</div><p className="mt-0.5 text-ink-3">{FIT_MEANING}</p></div>
              <div className="rounded-md border border-line bg-subtle p-3"><div className="font-semibold">Intent: up to {m.intent_max} points</div><p className="mt-0.5 text-ink-3">{INTENT_MEANING}</p></div>
            </div>
            <p className="mt-3 text-ink-2">The score is plain code. Same inputs, same score, every time, and each account page lists the rule behind every point.</p>
          </div>
          <div className="mt-3 overflow-x-auto">
            <table className="tbl">
              <thead><tr><th>Component</th><th>Part of</th><th>Rule</th><th className="r">Max points</th></tr></thead>
              <tbody>
                {m.components.map((c) => (
                  <tr key={c.name}><td className="whitespace-nowrap font-medium">{c.name}</td><td className="text-ink-3">{c.part_of}</td><td className="text-ink-2">{c.rule}</td><td className="r font-semibold">{c.max}</td></tr>
                ))}
              </tbody>
            </table>
          </div>
        </Panel>
      </section>

      <section id="intent" className="scroll-mt-20 grid gap-4 lg:grid-cols-2">
        <Panel title="3. Buying signals, weights and decay" flush>
          <div className="panel-pad pb-2 text-ink-2">
            A signal counts only if its quoted evidence appears in the research note. Points = weight × strength × confidence ×
            recency decay; only the newest signal of each type counts. Signals up to {m.decay.current_max_days} days old count in
            full, up to {m.decay.aging_max_days} days at ×{m.decay.aging_decay}, and older ones count for nothing. Intent is capped
            between 0 and {m.intent_max}.
          </div>
          <table className="tbl">
            <thead><tr><th>Signal</th><th className="r">Weight</th></tr></thead>
            <tbody>{Object.entries(m.signal_weights).sort((a, b) => b[1] - a[1]).map(([k, v]) => <tr key={k}><td>{signalLabel(k)}</td><td className="r font-medium">+{v}</td></tr>)}</tbody>
          </table>
        </Panel>
        <Panel title="Disqualifier penalties" flush>
          <div className="panel-pad pb-2 text-ink-2">
            Hard mismatches with the ICP subtract from intent. The same facts also lower fit, so a poor-fit account is penalised
            twice. That is a deliberate but debatable choice (see known weaknesses).
          </div>
          <table className="tbl">
            <thead><tr><th>Disqualifier</th><th className="r">Penalty</th></tr></thead>
            <tbody>{Object.entries(m.disqualifier_penalties).sort((a, b) => a[1] - b[1]).map(([k, v]) => <tr key={k}><td>{signalLabel(k)}</td><td className="r font-medium text-danger-700">{v}</td></tr>)}</tbody>
          </table>
        </Panel>
      </section>

      <section id="rules" className="scroll-mt-20">
        <Panel title="4. From score to recommended action" flush>
          <div className="panel-pad pb-2 text-ink-2">
            The total sets the tier ({m.tiers.map((t) => `${t.tier} ≥ ${t.min_total}`).join(", ")}). Then a fixed table picks the action
            from tier and intent. Within one tier, intent decides what sales does next.
          </div>
          <div className="overflow-x-auto" tabIndex={0}>
            <table className="tbl">
              <thead><tr><th>Rule</th><th>Tier</th><th>Intent</th><th>Action</th><th>In plain English</th></tr></thead>
              <tbody>
                {m.action_rules.map((r) => (
                  <tr key={r.rule_id}>
                    <td className="font-mono text-xs text-ink-3">{r.rule_id}</td><td>{r.tier}</td><td className="whitespace-nowrap">{r.condition}</td>
                    <td><ActionBadge action={r.action} /></td><td className="text-ink-2">{RULE_PLAIN[r.rule_id] ?? "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Panel>
      </section>

      <section id="evidence" className="scroll-mt-20 grid gap-4 lg:grid-cols-2">
        <Panel title="5. Evidence the system refuses to count">
          <p className="text-ink-2">Claims that fail these checks are recorded with a reason and contribute 0 points:</p>
          <dl className="mt-3 space-y-2">
            {Object.entries(m.rejection_categories).map(([k, v]) => (
              <div key={k}><dt className="font-semibold capitalize text-ink">{k}</dt><dd className="text-ink-3">{v}</dd></div>
            ))}
          </dl>
        </Panel>
        <Panel title="6. A person approves every message">
          <ul className="list-disc space-y-1.5 pl-5 text-ink-2">
            <li>Drafts are written only from verified evidence. A fact-check refuses any number not found in the evidence or account profile.</li>
            <li>Deprioritized accounts cannot get drafts; the rule table blocks it.</li>
            <li>Approving does not send. GTMOS has no code path that sends email: a person sends it, then logs it.</li>
          </ul>
        </Panel>
      </section>

      <section id="evaluation" className="scroll-mt-20 space-y-4">
        <Panel title="7. How well does it work? Evaluation on labelled data">
          <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
            <Kpi value={pct(ev.tier.accuracy)} label="Tier accuracy" hint={`${ev.tier.correct} of ${ev.tier.total} labelled accounts`} />
            <Kpi value={pct(ev.tier.recall["Priority 2"] ?? 0)} label="Priority 2 recall" hint="true P2 accounts found" />
            <Kpi value={pct(ev.tier.recall["Priority 1"] ?? 0)} label="Priority 1 recall" hint={`precision ${pct(ev.tier.precision["Priority 1"] ?? 0)}`} />
            <Kpi value={pct(ev.signals.precision)} label="Signal precision*" hint={`on ${ev.signals.total} simplified test sentences`} />
          </div>
          <div className="mt-5"><Confusion m={m} /></div>
          <div className="mt-4 space-y-2 rounded-md border border-warn-200 bg-warn-50 px-4 py-3 text-ink-2">
            <p><b className="font-semibold text-warn-700">Why Priority 2 recall is 0%.</b> The labelled accounts have no research notes,
              so the evaluation scores intent with the engine's built-in proxy (support-team size and funding stage). For good-fit
              companies that proxy adds enough points to push them past 90, so every true Priority 2 account is predicted
              Priority 1. In practice that means some accounts look more urgent than a person would rate them.</p>
            <p><b className="font-semibold text-warn-700">What the evaluation does not measure.</b> {ev.tier.method} *{ev.signals.method}</p>
          </div>
        </Panel>
      </section>

      <section id="weaknesses" className="scroll-mt-20">
        <Panel title="8. Known weaknesses">
          <dl className="divide-y divide-line">
            {WEAKNESSES.map(([t, d]) => (
              <div key={t} className="py-3 first:pt-0 last:pb-0"><dt className="font-semibold text-ink">{t}</dt><dd className="mt-0.5 text-ink-3">{d}</dd></div>
            ))}
          </dl>
        </Panel>
      </section>
    </div>
  );
}

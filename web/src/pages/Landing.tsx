import { Link } from "react-router-dom";
import { useEffect, useState } from "react";
import { ArrowRight, Check, Github, X } from "lucide-react";
import { api, type AccountDetail, type AccountRow, type Overview } from "../lib/api";
import { ActionBadge, ComponentBars, DataTag, Logo, ScoreBlock, TierBadge } from "../components/ui";
import { signalLabel } from "../lib/format";
import { SITE } from "../site";

function Nav() {
  return (
    <header className="sticky top-0 z-40 border-b border-line bg-surface/95 backdrop-blur">
      <div className="container-x flex h-14 items-center justify-between gap-4">
        <Logo />
        <nav className="hidden items-center gap-6 text-sm text-ink-3 md:flex" aria-label="Page sections">
          <a href="#how" className="hover:text-ink">How it works</a>
          <a href="#scoring" className="hover:text-ink">Scoring model</a>
          <a href="#guardrails" className="hover:text-ink">Guardrails</a>
          <Link to="/app/playground" className="hover:text-ink">Playground</Link>
        </nav>
        <div className="flex items-center gap-2">
          <a href={SITE.repoUrl} target="_blank" rel="noreferrer" className="btn-ghost hidden px-2.5 sm:inline-flex" aria-label="Source code on GitHub">
            <Github className="h-4 w-4" aria-hidden />
          </a>
          <Link to="/app" className="btn-secondary hidden sm:inline-flex">Explore GTMOS</Link>
          <Link to="/demo" className="btn-primary">5-minute demo</Link>
        </div>
      </div>
    </header>
  );
}

function LiveAccount() {
  const [detail, setDetail] = useState<AccountDetail | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    api.overview()
      .then((o) => (o.top_accounts[0] ? api.account(o.top_accounts[0].id) : null))
      .then(setDetail)
      .catch(() => setFailed(true));
  }, []);

  if (failed) {
    return (
      <div className="panel panel-pad text-ink-3">
        The live API is starting up. <Link to="/app" className="font-medium text-accent-700 hover:underline">Open the demo</Link> to retry.
      </div>
    );
  }
  if (!detail || !detail.score) {
    return <div className="panel h-[380px] animate-pulse bg-surface" aria-label="Loading live account" />;
  }
  const evidence = detail.signals.find((s) => !s.negative);
  return (
    <div className="panel">
      <div className="panel-head">
        <span className="eyebrow">Live account from the API</span>
        <DataTag />
      </div>
      <div className="panel-pad">
        <div className="flex items-start justify-between gap-4">
          <div className="min-w-0">
            <div className="truncate text-lg font-semibold text-ink">{detail.account.name}</div>
            <div className="mt-0.5 text-ink-3">{detail.account.industry} · {detail.account.employee_count} employees · {detail.account.country}</div>
            <div className="mt-2 flex flex-wrap items-center gap-1.5">
              <TierBadge tier={detail.score.tier} />
              <ActionBadge action={detail.recommendation?.action} />
            </div>
          </div>
          <ScoreBlock score={detail.score.total} size="md" />
        </div>
        <div className="mt-5"><ComponentBars components={detail.score.components} /></div>
        {evidence && (
          <blockquote className="mt-5 border-l-[3px] border-accent-600 pl-3">
            <div className="text-xs font-semibold text-ink-2">{signalLabel(evidence.type)} · {evidence.source}</div>
            <p className="mt-0.5 text-ink-2">“{evidence.evidence}”</p>
          </blockquote>
        )}
      </div>
      <div className="border-t border-line px-4 py-2.5 sm:px-5">
        <Link to={`/app/accounts/${detail.account.id}`} className="inline-flex items-center gap-1 text-sm font-medium text-accent-700 hover:underline">
          See the full breakdown <ArrowRight className="h-4 w-4" aria-hidden />
        </Link>
      </div>
    </div>
  );
}

function Facts() {
  const [o, setO] = useState<Overview | null>(null);
  useEffect(() => { api.overview().then(setO).catch(() => undefined); }, []);
  const items: [string | number | undefined, string][] = [
    [o?.counts.accounts, "synthetic accounts scored"],
    [o ? o.tiers["Priority 1"] + o.tiers["Priority 2"] : undefined, "rated Priority 1 or 2"],
    [o?.counts.signals, "buying signals, each quoting its source"],
    [0, "emails sent automatically"],
  ];
  return (
    <div className="border-b border-line bg-surface">
      <dl className="container-x grid grid-cols-2 lg:grid-cols-4">
        {items.map(([v, l], i) => (
          <div key={l} className={`py-5 ${i % 2 ? "pl-4 sm:pl-6" : ""} ${i > 0 ? "lg:border-l lg:border-line lg:pl-6" : ""}`}>
            <dd className="num text-2xl font-semibold tracking-tight text-ink">{v ?? "—"}</dd>
            <dt className="mt-0.5 text-ink-3">{l}</dt>
          </div>
        ))}
      </dl>
    </div>
  );
}

const QUESTIONS = [
  { q: "Who should we contact now?", a: "Every account gets a 100-point score you can audit line by line, then a tier and a next action from a fixed rule table." },
  { q: "Why does this account matter?", a: "Buying signals come from research notes and are kept only when the quoted evidence is actually in the source." },
  { q: "What should we say?", a: "Drafts use the strongest verified signals. A fact-check refuses any number that isn't in the evidence, and a person approves every message." },
];

const STEPS = [
  { t: "ICP", d: "Product description → structured ideal customer profile, validated against a schema.", who: "Model interprets" },
  { t: "Research", d: "Notes → candidate signals. Unquoted, negated or rumoured claims are dropped and recorded.", who: "Model interprets" },
  { t: "Score", d: "Five components, 100 points, one pure function. Same input, same score.", who: "Code decides" },
  { t: "Next action", d: "A rule table maps tier and intent to CONTACT, PRIORITIZE, NURTURE, RESEARCH or DEPRIORITIZE.", who: "Code decides" },
  { t: "Draft", d: "Outreach grounded in verified signals, under 120 words.", who: "Model writes" },
  { t: "Review", d: "Approve, edit or reject. Only approved drafts can be logged as sent.", who: "Person approves" },
];

const COMPONENTS = [
  { c: "ICP fit", p: 30, r: "Industry match and overlap with the ICP's pain points" },
  { c: "Buying intent", p: 20, r: "Verified signals × weight × confidence × recency, minus disqualifier penalties" },
  { c: "Company fit", p: 20, r: "Employee count inside the ICP range; exclusions remove points" },
  { c: "Technology fit", p: 15, r: "Overlap with the tools the ICP runs" },
  { c: "Geography fit", p: 15, r: "Country inside the target regions" },
];

const GUARDRAILS = [
  { t: "The model interprets; code decides", d: "The LLM never scores, filters or does arithmetic. Business rules live in tested Python." },
  { t: "Evidence on every claim", d: "Each signal stores its quote, source, date and confidence. Every score explains itself rule by rule." },
  { t: "Grounded drafts only", d: "Numbers in a draft must appear in the account profile or evidence, or the draft is refused." },
  { t: "People send, not the system", d: "No code path sends email. A draft must be approved before it can even be logged as sent." },
];

function RumourTest() {
  const [acme, setAcme] = useState<AccountRow | null>(null);
  useEffect(() => {
    api.accounts().then((rows) => setAcme(rows.find((r) => r.name === "Acme Technologies") ?? null)).catch(() => undefined);
  }, []);
  return (
    <section className="container-x py-14 sm:py-20" aria-labelledby="rumour">
      <div className="grid gap-8 lg:grid-cols-2">
        <div>
          <div className="eyebrow">Worked example</div>
          <h2 id="rumour" className="mt-2 text-2xl font-semibold tracking-tight sm:text-3xl">A near-perfect fit with no reason to call</h2>
          <p className="mt-3 text-ink-2">
            Acme Technologies matches the ICP closely: B2B SaaS, 240 employees, US, runs Zendesk. A keyword matcher sees
            “hiring” and “support team” in its research notes and flags it as hot.
          </p>
          <p className="mt-3 text-ink-2">
            GTMOS reads the sentence. The hiring was a rumour and the CEO confirmed a freeze, so intent stays at zero and the
            account lands in Priority 3 instead of on the call list.
          </p>
          {acme && (
            <Link to={`/app/accounts/${acme.id}`} className="mt-4 inline-flex items-center gap-1 font-medium text-accent-700 hover:underline">
              Inspect Acme's live score <ArrowRight className="h-4 w-4" aria-hidden />
            </Link>
          )}
        </div>
        <div className="space-y-3">
          <figure className="panel panel-pad">
            <figcaption className="eyebrow">Research note · News article</figcaption>
            <blockquote className="mt-2 text-ink-2">
              “<mark className="rounded-sm bg-warn-50 px-0.5 text-warn-700">Rumors suggested</mark> Acme was hiring for a massive support
              team expansion, but their CEO recently confirmed a <mark className="rounded-sm bg-danger-50 px-0.5 text-danger-700">hiring freeze</mark> for all non-engineering roles.”
            </blockquote>
          </figure>
          <div className="grid gap-3 sm:grid-cols-2">
            <div className="panel panel-pad">
              <div className="flex items-center gap-1.5 font-semibold text-danger-700"><X className="h-4 w-4" aria-hidden /> Keyword matcher</div>
              <p className="mt-1 text-ink-3">“support_hiring” detected · +14.4 intent · call this week</p>
            </div>
            <div className="panel panel-pad">
              <div className="flex items-center gap-1.5 font-semibold text-accent-700"><Check className="h-4 w-4" aria-hidden /> GTMOS</div>
              <p className="mt-1 text-ink-3">Negated claim, recorded as rejected · intent {acme ? acme.intent_score.toFixed(1) : "0.0"} / 20 · {acme ? acme.tier : "Priority 3"}</p>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

const WHO_STYLE: Record<string, string> = {
  "Code decides": "border-accent-600 bg-accent-50 text-accent-700",
  "Person approves": "border-warn-200 bg-warn-50 text-warn-700",
};

export default function Landing() {
  return (
    <div className="min-h-screen bg-canvas">
      <Nav />

      <section className="border-b border-line bg-surface">
        <div className="container-x grid items-start gap-10 py-12 sm:py-16 lg:grid-cols-[1.1fr_0.9fr]">
          <div>
            <div className="eyebrow">Account intelligence for B2B sales teams</div>
            <h1 className="mt-3 text-4xl font-semibold leading-[1.1] tracking-tight text-ink sm:text-5xl">
              Know which accounts to work, why now, and what to say.
            </h1>
            <p className="mt-4 max-w-xl text-base text-ink-2">
              GTMOS turns a product description into a scored, evidence-backed account list, recommends the next action
              from explicit rules, and drafts outreach that a person approves before anything is sent.
            </p>
            <div className="mt-6 flex flex-wrap gap-2">
              <Link to="/demo" className="btn-primary px-4 py-2.5">Explore the 5-minute demo <ArrowRight className="h-4 w-4" aria-hidden /></Link>
              <Link to="/app" className="btn-secondary px-4 py-2.5">Explore GTMOS</Link>
            </div>
            <ul className="mt-6 grid gap-2 text-ink-2 sm:grid-cols-2">
              {["Deterministic 100-point scoring", "Quoted evidence for every signal", "Rejected claims recorded, not hidden", "Human approval for all outreach"].map((t) => (
                <li key={t} className="flex items-center gap-2"><Check className="h-4 w-4 text-accent-600" aria-hidden /> {t}</li>
              ))}
            </ul>
            <p className="mt-6 text-xs text-ink-4">
              Demo data is synthetic and the pipeline is simulated. Model evaluation: 57% tier accuracy on a labelled set
              (<Link to="/app/methodology#evaluation" className="underline hover:text-ink">methodology and limitations</Link>).
            </p>
          </div>
          <LiveAccount />
        </div>
      </section>

      <Facts />

      <section className="container-x py-14 sm:py-20" aria-labelledby="questions">
        <div className="eyebrow">What it answers</div>
        <h2 id="questions" className="mt-2 text-2xl font-semibold tracking-tight sm:text-3xl">Three questions outbound teams ask every week</h2>
        <div className="mt-8 grid gap-px overflow-hidden rounded-lg border border-line bg-line md:grid-cols-3">
          {QUESTIONS.map(({ q, a }) => (
            <div key={q} className="bg-surface p-5">
              <h3 className="font-semibold text-ink">{q}</h3>
              <p className="mt-1.5 leading-relaxed text-ink-3">{a}</p>
            </div>
          ))}
        </div>
      </section>

      <section id="how" className="scroll-mt-16 border-y border-line bg-surface py-14 sm:py-20" aria-labelledby="how-title">
        <div className="container-x">
          <div className="eyebrow">How it works</div>
          <h2 id="how-title" className="mt-2 text-2xl font-semibold tracking-tight sm:text-3xl">The model reads and writes. Code makes the decisions.</h2>
          <p className="mt-3 max-w-2xl text-ink-2">
            Six stages with a clear owner each. Language models handle the unstructured parts; anything that decides who gets
            contacted is plain, tested code.
          </p>
          <ol className="mt-8 overflow-hidden rounded-lg border border-line">
            {STEPS.map(({ t, d, who }, i) => (
              <li key={t} className="grid grid-cols-[40px_1fr] items-start gap-3 border-b border-line px-4 py-3.5 last:border-b-0 sm:grid-cols-[40px_160px_1fr_150px] sm:items-center">
                <span className="num text-ink-4">{String(i + 1).padStart(2, "0")}</span>
                <span className="font-semibold text-ink">{t}</span>
                <span className="col-span-2 text-ink-3 sm:col-span-1">{d}</span>
                <span className={`badge col-span-2 w-fit sm:col-span-1 sm:justify-self-end ${WHO_STYLE[who] ?? "border-line-strong bg-subtle text-ink-3"}`}>{who}</span>
              </li>
            ))}
          </ol>
        </div>
      </section>

      <section id="scoring" className="container-x scroll-mt-16 py-14 sm:py-20" aria-labelledby="scoring-title">
        <div className="grid gap-10 lg:grid-cols-[0.85fr_1.15fr]">
          <div>
            <div className="eyebrow">Scoring model</div>
            <h2 id="scoring-title" className="mt-2 text-2xl font-semibold tracking-tight sm:text-3xl">100 points you can argue with</h2>
            <p className="mt-3 text-ink-2">
              No black-box propensity score. Every point traces to a named rule, so sales and RevOps can see why an account
              ranked where it did, and change the rule if they disagree.
            </p>
            <table className="tbl mt-6 overflow-hidden rounded-lg border border-line bg-surface">
              <thead><tr><th>Tier</th><th className="r">Total score</th></tr></thead>
              <tbody>
                {([["Priority 1", "90 and above"], ["Priority 2", "75 – 89.9"], ["Priority 3", "50 – 74.9"], ["Low", "below 50"]] as const).map(([t, r]) => (
                  <tr key={t}><td><TierBadge tier={t} /></td><td className="r text-ink-2">{r}</td></tr>
                ))}
              </tbody>
            </table>
          </div>
          <table className="tbl self-start overflow-hidden rounded-lg border border-line bg-surface">
            <thead><tr><th>Component</th><th>Rule</th><th className="r">Max</th></tr></thead>
            <tbody>
              {COMPONENTS.map(({ c, p, r }) => (
                <tr key={c}><td className="whitespace-nowrap font-semibold">{c}</td><td className="text-ink-3">{r}</td><td className="r font-semibold">{p}</td></tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <div className="border-y border-line bg-surface"><RumourTest /></div>

      <section id="guardrails" className="container-x scroll-mt-16 py-14 sm:py-20" aria-labelledby="guardrails-title">
        <div className="eyebrow">Guardrails</div>
        <h2 id="guardrails-title" className="mt-2 text-2xl font-semibold tracking-tight sm:text-3xl">Designed to be trusted with a pipeline</h2>
        <dl className="mt-8 grid gap-px overflow-hidden rounded-lg border border-line bg-line sm:grid-cols-2">
          {GUARDRAILS.map(({ t, d }) => (
            <div key={t} className="bg-surface p-5">
              <dt className="font-semibold text-ink">{t}</dt>
              <dd className="mt-1.5 leading-relaxed text-ink-3">{d}</dd>
            </div>
          ))}
        </dl>
      </section>

      <section className="border-t border-line bg-surface">
        <div className="container-x flex flex-col items-start justify-between gap-4 py-10 sm:flex-row sm:items-center">
          <div>
            <h2 className="text-xl font-semibold tracking-tight">Paste a research note. See how it scores.</h2>
            <p className="mt-1 text-ink-3">The playground runs the real extractor, scorer and rule table. Nothing you type is stored.</p>
          </div>
          <div className="flex gap-2">
            <Link to="/app/playground" className="btn-primary">Try the playground</Link>
            <Link to="/app/review" className="btn-secondary">Review AI drafts</Link>
          </div>
        </div>
      </section>

      <footer className="border-t border-line">
        <div className="container-x flex flex-col gap-4 py-8 text-xs text-ink-3 md:flex-row md:items-center md:justify-between">
          <div className="flex items-center gap-4">
            <Logo />
            <span className="hidden sm:inline">Python · FastAPI · SQLAlchemy · Pydantic · React</span>
          </div>
          <p className="max-w-md">All companies, contacts and signals are synthetic. The pipeline is simulated. The public demo runs its language model offline.</p>
          <div className="flex gap-4">
            <a href={SITE.repoUrl} target="_blank" rel="noreferrer" className="hover:text-ink">GitHub</a>
            <a href="/api/docs" className="hover:text-ink">API docs</a>
            {SITE.authorUrl && <a href={SITE.authorUrl} target="_blank" rel="noreferrer" className="hover:text-ink">{SITE.authorName}</a>}
          </div>
        </div>
      </footer>
    </div>
  );
}

import { Link } from "react-router-dom";
import { useEffect, useState } from "react";
import {
  ArrowRight, BadgeCheck, Bot, Braces, CheckCircle2, Code2, FileSearch, Github, Hand, Layers,
  MessageSquareQuote, Radar, ScrollText, ShieldCheck, Target, UserCheck, XCircle,
} from "lucide-react";
import { api, type AccountDetail, type AccountRow, type Overview } from "../lib/api";
import { ActionBadge, ComponentBars, Logo, ScoreRing, TierBadge } from "../components/ui";
import { signalLabel } from "../lib/format";
import { SITE } from "../site";

function Nav() {
  return (
    <header className="sticky top-0 z-40 border-b border-ink-800/80 bg-ink-950/75 backdrop-blur-md">
      <div className="container-x flex h-16 items-center justify-between gap-4">
        <Logo />
        <nav className="hidden items-center gap-7 text-sm text-mist-400 md:flex">
          <a href="#how" className="hover:text-mist-100">How it works</a>
          <a href="#scoring" className="hover:text-mist-100">Scoring</a>
          <a href="#guardrails" className="hover:text-mist-100">Guardrails</a>
          <Link to="/app/playground" className="hover:text-mist-100">Playground</Link>
        </nav>
        <div className="flex items-center gap-2">
          <a href={SITE.repoUrl} target="_blank" rel="noreferrer" className="btn-ghost hidden px-3 sm:inline-flex" aria-label="Source code on GitHub">
            <Github className="h-4 w-4" />
          </a>
          <Link to="/app" className="btn-primary">Live demo <ArrowRight className="h-4 w-4" /></Link>
        </div>
      </div>
    </header>
  );
}

function HeroCard() {
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
      <div className="card card-pad text-sm text-mist-400">
        The live API is waking up. <Link to="/app" className="text-signal-400 underline">Open the demo</Link> to retry.
      </div>
    );
  }
  if (!detail || !detail.score) {
    return <div className="card h-[420px] animate-pulse bg-ink-900" aria-label="Loading live account" />;
  }
  const evidence = detail.signals.find((s) => !s.negative);
  return (
    <div className="card relative overflow-hidden p-5 shadow-glow sm:p-6">
      <div className="mb-4 flex items-center justify-between gap-3">
        <div className="flex items-center gap-2 font-mono text-[11px] uppercase tracking-[0.16em] text-mist-500">
          <span className="pulse-dot h-1.5 w-1.5 rounded-full bg-signal-400" /> Live from the API
        </div>
        <TierBadge tier={detail.score.tier} />
      </div>
      <div className="flex items-center gap-5">
        <ScoreRing score={detail.score.total} size={104} />
        <div className="min-w-0">
          <div className="truncate font-display text-xl font-semibold">{detail.account.name}</div>
          <div className="mt-0.5 text-sm text-mist-400">
            {detail.account.industry} · {detail.account.employee_count} employees · {detail.account.country}
          </div>
          <div className="mt-2 flex items-center gap-2 text-xs text-mist-400">
            Next action <ActionBadge action={detail.recommendation?.action} />
          </div>
        </div>
      </div>
      <div className="mt-6"><ComponentBars components={detail.score.components} /></div>
      {evidence && (
        <div className="mt-5 rounded-xl border border-ink-700 bg-ink-850 p-4">
          <div className="mb-1 flex items-center gap-2 text-xs font-semibold text-signal-300">
            <MessageSquareQuote className="h-3.5 w-3.5" /> {signalLabel(evidence.type)} · {evidence.source}
          </div>
          <p className="text-sm leading-relaxed text-mist-300">“{evidence.evidence}”</p>
        </div>
      )}
      <Link to={`/app/accounts/${detail.account.id}`} className="mt-5 inline-flex items-center gap-1 text-sm font-medium text-signal-400 hover:text-signal-300">
        See the full breakdown <ArrowRight className="h-4 w-4" />
      </Link>
    </div>
  );
}

function LiveStats() {
  const [o, setO] = useState<Overview | null>(null);
  useEffect(() => { api.overview().then(setO).catch(() => undefined); }, []);
  const items = [
    { v: o?.counts.accounts, l: "accounts scored" },
    { v: o?.counts.signals, l: "signals verified with evidence" },
    { v: o ? o.tiers["Priority 1"] + o.tiers["Priority 2"] : undefined, l: "worth contacting this week" },
    { v: 0, l: "emails sent automatically" },
  ];
  return (
    <div className="grid grid-cols-2 gap-px overflow-hidden rounded-2xl border border-ink-700 bg-ink-700 lg:grid-cols-4">
      {items.map((it) => (
        <div key={it.l} className="bg-ink-900 px-5 py-6">
          <div className="font-display text-3xl font-semibold tabular-nums sm:text-4xl">{it.v ?? "—"}</div>
          <div className="mt-1 text-sm text-mist-400">{it.l}</div>
        </div>
      ))}
    </div>
  );
}

const QUESTIONS = [
  { icon: Target, q: "Who should I contact right now?", a: "Every account gets a 100-point score you can audit line by line, then a tier and a next action." },
  { icon: Radar, q: "Why do they matter?", a: "Buying signals are pulled from research notes and kept only if the quoted evidence is really in the source." },
  { icon: MessageSquareQuote, q: "What should I say to them?", a: "Drafts are built from the top verified signals. A fact-check rejects any number that isn't in the evidence." },
];

const STEPS = [
  { n: "01", icon: Bot, t: "ICP engine", d: "Product description → structured ideal customer profile, validated by Pydantic.", who: "LLM interprets" },
  { n: "02", icon: FileSearch, t: "Research", d: "Notes → candidate signals. Unquoted, negated or rumoured claims are dropped.", who: "LLM interprets" },
  { n: "03", icon: Braces, t: "Scoring", d: "Five components, 100 points, pure function. Same input, same score, every time.", who: "Code decides" },
  { n: "04", icon: Layers, t: "Next action", d: "A rule table maps tier and intent to CONTACT, NURTURE, RESEARCH and more.", who: "Code decides" },
  { n: "05", icon: ScrollText, t: "Draft", d: "Outreach grounded in the top three verified signals, under 120 words.", who: "LLM writes" },
  { n: "06", icon: UserCheck, t: "Human review", d: "Approve, edit or reject. Only approved drafts can be logged as sent.", who: "Human approves" },
];

const COMPONENTS = [
  { c: "ICP fit", p: 30, r: "Industry match + overlap with the ICP's pain points" },
  { c: "Buying intent", p: 20, r: "Verified signals × weight × confidence × recency decay" },
  { c: "Company fit", p: 20, r: "Employee count inside the ICP range; exclusions force 0" },
  { c: "Technology fit", p: 15, r: "Overlap with the tools the ICP runs" },
  { c: "Geography fit", p: 15, r: "Country inside the target regions" },
];

const GUARDRAILS = [
  { icon: Code2, t: "AI interprets, code decides", d: "The LLM never scores, filters or does arithmetic. Business rules live in tested Python." },
  { icon: BadgeCheck, t: "Evidence on every claim", d: "Each signal stores the quote, source, date and confidence. Open any account to see why." },
  { icon: ShieldCheck, t: "Grounded drafts only", d: "Numbers in a draft must appear in the account profile or evidence, or the draft is refused." },
  { icon: Hand, t: "Humans send, not robots", d: "No code path sends email. Approval is required before a draft can even be marked as sent." },
];

function RumorTest() {
  const [acme, setAcme] = useState<AccountRow | null>(null);
  useEffect(() => {
    api.accounts().then((rows) => setAcme(rows.find((r) => r.name === "Acme Technologies") ?? null)).catch(() => undefined);
  }, []);
  return (
    <section className="container-x py-20 sm:py-28">
      <div className="grid items-center gap-10 lg:grid-cols-2">
        <div>
          <div className="eyebrow">The rumour test</div>
          <h2 className="h-display mt-3 text-3xl sm:text-4xl">A perfect-fit account with no reason to call</h2>
          <p className="mt-4 text-mist-400">
            Acme Technologies matches the ICP almost perfectly: B2B SaaS, 240 employees, US, runs Zendesk. A keyword
            matcher sees “hiring” and “support team” in its research notes and flags it hot.
          </p>
          <p className="mt-3 text-mist-400">
            GTMOS reads the sentence. The hiring was a rumour, and the CEO confirmed a freeze. Intent stays at zero, so the
            account lands in Priority 3 instead of your SDR's call list.
          </p>
          {acme && (
            <Link to={`/app/accounts/${acme.id}`} className="mt-6 inline-flex items-center gap-1 text-sm font-medium text-signal-400 hover:text-signal-300">
              Inspect Acme's live score <ArrowRight className="h-4 w-4" />
            </Link>
          )}
        </div>
        <div className="space-y-3">
          <div className="card card-pad">
            <div className="mb-2 font-mono text-[11px] uppercase tracking-[0.16em] text-mist-500">Research note · News article</div>
            <p className="text-mist-300">
              “<mark className="rounded bg-amberx-400/15 px-1 text-amberx-400">Rumors suggested</mark> Acme was hiring for a massive
              support team expansion, but their CEO recently confirmed a <mark className="rounded bg-rose-400/15 px-1 text-rose-400">hiring freeze</mark> for all non-engineering roles.”
            </p>
          </div>
          <div className="grid gap-3 sm:grid-cols-2">
            <div className="card card-pad border-rose-400/25">
              <div className="flex items-center gap-2 text-sm font-semibold text-rose-400"><XCircle className="h-4 w-4" /> Keyword matcher</div>
              <p className="mt-2 text-sm text-mist-400">“support_hiring” detected · +14.4 intent · call this week</p>
            </div>
            <div className="card card-pad border-signal-400/30">
              <div className="flex items-center gap-2 text-sm font-semibold text-signal-300"><CheckCircle2 className="h-4 w-4" /> GTMOS</div>
              <p className="mt-2 text-sm text-mist-400">
                Negated claim, no signal · intent {acme ? acme.intent_score.toFixed(1) : "0.0"} / 20 · {acme ? acme.tier : "Priority 3"}
              </p>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

export default function Landing() {
  return (
    <div className="min-h-screen">
      <Nav />

      {/* Hero */}
      <section className="relative overflow-hidden border-b border-ink-800">
        <div className="grid-bg absolute inset-0 [mask-image:radial-gradient(ellipse_at_top,black_30%,transparent_75%)]" aria-hidden />
        <div className="absolute -top-40 left-1/2 h-[480px] w-[720px] -translate-x-1/2 rounded-full bg-signal-500/10 blur-3xl" aria-hidden />
        <div className="container-x relative grid items-center gap-12 py-16 sm:py-24 lg:grid-cols-[1.1fr_0.9fr]">
          <div className="rise">
            <div className="chip border-signal-400/30 bg-signal-400/10 text-signal-300">
              <span className="pulse-dot h-1.5 w-1.5 rounded-full bg-signal-400" /> Explainable GTM intelligence
            </div>
            <h1 className="h-display mt-6 text-[2.6rem] leading-[1.04] sm:text-6xl">
              Know who to contact,<br />
              <span className="text-signal-400">why now</span>, and what to say.
            </h1>
            <p className="mt-6 max-w-xl text-lg text-mist-400">
              GTMOS turns a product description into a scored, evidence-backed target list. It drafts outreach from verified
              buying signals, then waits for a human to approve every message.
            </p>
            <div className="mt-8 flex flex-wrap gap-3">
              <Link to="/app" className="btn-primary px-5 py-3 text-base">Open the live demo <ArrowRight className="h-4 w-4" /></Link>
              <Link to="/app/playground" className="btn-ghost px-5 py-3 text-base">Score a company</Link>
            </div>
            <ul className="mt-8 flex flex-wrap gap-x-6 gap-y-2 text-sm text-mist-400">
              <li className="flex items-center gap-2"><CheckCircle2 className="h-4 w-4 text-signal-400" /> Deterministic 100-pt scoring</li>
              <li className="flex items-center gap-2"><CheckCircle2 className="h-4 w-4 text-signal-400" /> Evidence on every signal</li>
              <li className="flex items-center gap-2"><CheckCircle2 className="h-4 w-4 text-signal-400" /> Human-approved outreach</li>
            </ul>
          </div>
          <div className="rise [animation-delay:120ms]"><HeroCard /></div>
        </div>
      </section>

      <section className="container-x -mt-px py-12"><LiveStats /></section>

      {/* Three questions */}
      <section className="container-x py-16 sm:py-20">
        <div className="max-w-2xl">
          <div className="eyebrow">What it answers</div>
          <h2 className="h-display mt-3 text-3xl sm:text-4xl">Three questions every outbound team asks on Monday</h2>
        </div>
        <div className="mt-10 grid gap-4 md:grid-cols-3">
          {QUESTIONS.map(({ icon: Icon, q, a }) => (
            <div key={q} className="card card-pad transition hover:border-ink-600">
              <Icon className="h-6 w-6 text-signal-400" />
              <h3 className="mt-4 font-display text-lg font-semibold">{q}</h3>
              <p className="mt-2 text-sm leading-relaxed text-mist-400">{a}</p>
            </div>
          ))}
        </div>
      </section>

      {/* How it works */}
      <section id="how" className="scroll-mt-20 border-y border-ink-800 bg-ink-900/40 py-16 sm:py-24">
        <div className="container-x">
          <div className="max-w-2xl">
            <div className="eyebrow">How it works</div>
            <h2 className="h-display mt-3 text-3xl sm:text-4xl">The LLM reads and writes. Code makes the calls.</h2>
            <p className="mt-4 text-mist-400">
              Six stages, each with a clear owner. Language models handle the fuzzy parts; anything that decides who gets
              contacted is plain, tested code.
            </p>
          </div>
          <ol className="mt-12 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {STEPS.map(({ n, icon: Icon, t, d, who }) => (
              <li key={n} className="card card-pad relative">
                <div className="flex items-center justify-between">
                  <span className="font-mono text-xs text-mist-500">{n}</span>
                  <span className={`chip ${who === "Code decides" ? "border-signal-400/40 text-signal-300" : who === "Human approves" ? "border-amberx-400/40 text-amberx-400" : "border-sky-400/40 text-sky-400"}`}>
                    {who}
                  </span>
                </div>
                <Icon className="mt-5 h-6 w-6 text-mist-300" />
                <h3 className="mt-3 font-display text-lg font-semibold">{t}</h3>
                <p className="mt-1.5 text-sm leading-relaxed text-mist-400">{d}</p>
              </li>
            ))}
          </ol>
        </div>
      </section>

      {/* Scoring */}
      <section id="scoring" className="container-x scroll-mt-20 py-16 sm:py-24">
        <div className="grid gap-10 lg:grid-cols-[0.9fr_1.1fr]">
          <div>
            <div className="eyebrow">Explainable scoring</div>
            <h2 className="h-display mt-3 text-3xl sm:text-4xl">100 points you can argue with</h2>
            <p className="mt-4 text-mist-400">
              No black-box propensity model. Every point traces to a named rule, so sales and RevOps can see exactly why an
              account ranked where it did, and change the rule if they disagree.
            </p>
            <div className="mt-8 grid grid-cols-2 gap-3 text-sm">
              {[
                ["Priority 1", "90+", "text-signal-300"],
                ["Priority 2", "75–89", "text-sky-400"],
                ["Priority 3", "50–74", "text-amberx-400"],
                ["Low", "< 50", "text-mist-400"],
              ].map(([t, r, c]) => (
                <div key={t} className="rounded-xl border border-ink-700 bg-ink-900 px-4 py-3">
                  <div className={`font-semibold ${c}`}>{t}</div>
                  <div className="font-mono text-xs text-mist-500">{r} points</div>
                </div>
              ))}
            </div>
          </div>
          <div className="card overflow-hidden">
            {COMPONENTS.map(({ c, p, r }, i) => (
              <div key={c} className={`flex items-center gap-4 px-5 py-5 sm:px-6 ${i ? "border-t border-ink-800" : ""}`}>
                <div className="w-14 shrink-0 font-display text-2xl font-semibold tabular-nums text-signal-400">{p}</div>
                <div className="min-w-0">
                  <div className="font-semibold">{c}</div>
                  <div className="text-sm text-mist-400">{r}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      <div className="border-y border-ink-800 bg-ink-900/40"><RumorTest /></div>

      {/* Guardrails */}
      <section id="guardrails" className="container-x scroll-mt-20 py-16 sm:py-24">
        <div className="max-w-2xl">
          <div className="eyebrow">Guardrails</div>
          <h2 className="h-display mt-3 text-3xl sm:text-4xl">Built to be trusted with your pipeline</h2>
        </div>
        <div className="mt-10 grid gap-4 sm:grid-cols-2">
          {GUARDRAILS.map(({ icon: Icon, t, d }) => (
            <div key={t} className="card card-pad flex gap-4">
              <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl border border-ink-700 bg-ink-850">
                <Icon className="h-5 w-5 text-signal-400" />
              </div>
              <div>
                <h3 className="font-display text-lg font-semibold">{t}</h3>
                <p className="mt-1 text-sm leading-relaxed text-mist-400">{d}</p>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* CTA */}
      <section className="container-x pb-20">
        <div className="relative overflow-hidden rounded-3xl border border-signal-400/25 bg-gradient-to-br from-ink-850 to-ink-900 px-6 py-12 text-center sm:px-12 sm:py-16">
          <div className="absolute -bottom-32 left-1/2 h-64 w-[600px] -translate-x-1/2 rounded-full bg-signal-500/15 blur-3xl" aria-hidden />
          <h2 className="h-display relative text-3xl sm:text-4xl">Paste a research note. Watch it get scored.</h2>
          <p className="relative mx-auto mt-4 max-w-xl text-mist-400">
            The playground runs the real signal extractor, scoring engine and rule table on any company you describe.
            Nothing you type is stored.
          </p>
          <div className="relative mt-8 flex flex-wrap justify-center gap-3">
            <Link to="/app/playground" className="btn-primary px-5 py-3 text-base">Try the playground <ArrowRight className="h-4 w-4" /></Link>
            <Link to="/app/review" className="btn-ghost px-5 py-3 text-base">Review AI drafts</Link>
          </div>
        </div>
      </section>

      <footer className="border-t border-ink-800">
        <div className="container-x flex flex-col gap-6 py-10 text-sm text-mist-500 md:flex-row md:items-center md:justify-between">
          <div className="flex items-center gap-4">
            <Logo />
            <span className="hidden sm:inline">Python · FastAPI · SQLAlchemy · Pydantic · React</span>
          </div>
          <p className="max-w-md">
            All companies, contacts and signals are synthetic demo data. The public demo runs the LLM layer in offline mock mode.
          </p>
          <div className="flex gap-4">
            <a href={SITE.repoUrl} target="_blank" rel="noreferrer" className="hover:text-mist-100">GitHub</a>
            <a href="/api/docs" className="hover:text-mist-100">API docs</a>
            {SITE.authorUrl && <a href={SITE.authorUrl} target="_blank" rel="noreferrer" className="hover:text-mist-100">{SITE.authorName}</a>}
          </div>
        </div>
      </footer>
    </div>
  );
}

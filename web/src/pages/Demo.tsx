import { useEffect } from "react";
import { Link, useNavigate } from "react-router-dom";
import { ArrowRight } from "lucide-react";
import { DataTag, Logo } from "../components/ui";
import { useDemo } from "../demo/DemoContext";
import { STEPS, TOTAL } from "../demo/steps";

export default function DemoPage() {
  const demo = useDemo();
  const navigate = useNavigate();
  useEffect(() => { demo.preload(); }, [demo]);

  function begin(i: number) {
    demo.start(i);
    navigate(STEPS[i].target(demo.accounts));
  }

  return (
    <div className="min-h-screen bg-canvas">
      <header className="border-b border-line bg-surface">
        <div className="container-x flex h-14 items-center justify-between">
          <Logo />
          <div className="flex items-center gap-2">
            <DataTag>Synthetic data · offline AI</DataTag>
            <Link to="/app" className="btn-secondary hidden sm:inline-flex">Explore GTMOS</Link>
          </div>
        </div>
      </header>

      <main className="container-x py-10 sm:py-14">
        <div className="max-w-3xl">
          <div className="eyebrow">Guided demonstration · about {Math.round(TOTAL / 60)} minutes</div>
          <h1 className="mt-2 text-3xl font-semibold tracking-tight text-ink sm:text-4xl">
            150 accounts. Limited sales capacity. Which ones deserve your team's attention?
          </h1>
          <p className="mt-4 text-base text-ink-2">
            You lead go-to-market at a B2B SaaS company with incomplete information about every account. This tour walks
            through the real GTMOS application, step by step, to show how it separates <b className="font-semibold text-ink">fit</b> (does
            the company look like our customer?) from <b className="font-semibold text-ink">intent</b> (is there credible evidence of a
            reason to act now?), and why that changes what the sales team does next.
          </p>
          <div className="mt-6 flex flex-wrap gap-2">
            <button className="btn-primary px-4 py-2.5" disabled={!demo.ready} onClick={() => begin(0)}>{demo.ready ? "" : "Loading… "}Start the 5-minute demo <ArrowRight className="h-4 w-4" aria-hidden /></button>
            {demo.active && demo.step > 0 && (
              <button className="btn-secondary px-4 py-2.5" disabled={!demo.ready} onClick={() => begin(demo.step)}>Resume at step {demo.step + 1}</button>
            )}
            <Link to="/app" className="btn-secondary px-4 py-2.5">Explore GTMOS on your own</Link>
          </div>
        </div>

        <ol className="mt-10 overflow-hidden rounded-lg border border-line bg-surface">
          {STEPS.map((s, i) => (
            <li key={s.title} className="grid grid-cols-[36px_1fr] gap-x-3 gap-y-2 border-b border-line px-4 py-4 last:border-b-0 sm:grid-cols-[36px_1fr_auto] sm:items-center sm:px-5">
              <span className="num flex h-7 w-7 items-center justify-center rounded-full border border-line-strong text-xs font-semibold text-ink-2">{i + 1}</span>
              <div className="min-w-0">
                <div className="flex flex-wrap items-baseline gap-x-2">
                  <h2 className="font-semibold text-ink">{s.title}</h2>
                  <span className="num text-xs text-ink-4">{s.duration}</span>
                  <span className="text-xs text-ink-4">· {s.screen}</span>
                </div>
                <p className="mt-0.5 text-ink-3">{s.summary}</p>
              </div>
              <button className="btn-secondary col-start-2 w-fit py-1.5 text-xs sm:col-start-auto" disabled={!demo.ready} onClick={() => begin(i)}>Jump to step {i + 1}</button>
            </li>
          ))}
        </ol>

        <section className="mt-8 grid gap-4 md:grid-cols-2" aria-label="About this demo">
          <div className="panel panel-pad">
            <h2 className="h-section">What is real and what is not</h2>
            <ul className="mt-2 list-disc space-y-1 pl-5 text-ink-2">
              <li>Every company, contact and research note is synthetic. Company 36 B2B and Company 37 Cloud include labelled synthetic demo notes.</li>
              <li>The pipeline and its conversion numbers are a 40-day simulation, not sales results.</li>
              <li>The language model runs offline. No email is ever sent.</li>
              <li>Your actions stay in a temporary per-browser sandbox (about two hours, on one server) and can reset.</li>
            </ul>
          </div>
          <div className="panel panel-pad">
            <h2 className="h-section">How well does the model work?</h2>
            <p className="mt-2 text-ink-2">
              On a labelled evaluation set, tier accuracy is 57%, and Priority 2 recall is 0% (true Priority 2 accounts are all
              scored as Priority 1). The methodology page explains why, what the evaluation does and doesn't measure, and other
              known weaknesses.
            </p>
            <Link to="/app/methodology#evaluation" className="mt-2 inline-flex items-center gap-1 font-medium text-accent-700 hover:underline">Read the methodology <ArrowRight className="h-4 w-4" aria-hidden /></Link>
          </div>
        </section>
      </main>
    </div>
  );
}

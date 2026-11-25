import { useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { ArrowLeft, ArrowRight, Check, ChevronDown, ChevronUp, RotateCcw, X } from "lucide-react";
import { useDemo } from "../demo/DemoContext";
import { STEPS } from "../demo/steps";

/** Floating guide shown over the real application while the 5-minute demo is active. */
export default function DemoGuide() {
  const demo = useDemo();
  const navigate = useNavigate();
  const location = useLocation();
  const [collapsed, setCollapsed] = useState(false);
  if (!demo.active) return null;

  const step = STEPS[demo.step];
  const target = step.target(demo.accounts);
  const here = location.pathname + location.search === target.split("#")[0];
  const missing = (step.needs ?? []).filter((k) => !demo.accounts[k]);
  const loadingAccounts = (step.needs?.length ?? 0) > 0 && !demo.ready;

  function goTo(i: number) {
    demo.go(i);
    navigate(STEPS[i].target(demo.accounts));
    setCollapsed(false);
  }

  return (
    <aside
      aria-label="Guided demo"
      className="fixed inset-x-0 bottom-0 z-40 border-t border-line bg-surface shadow-[0_-4px_16px_rgba(16,24,40,0.08)] lg:sticky lg:top-0 lg:h-screen lg:overflow-y-auto lg:border-l lg:border-t-0 lg:shadow-none"
    >
      <div className="flex items-center gap-2 border-b border-line px-4 py-2.5">
        <span className="eyebrow">5-minute demo · Step {demo.step + 1} of {STEPS.length}</span>
        <span className="num text-2xs text-ink-4">~{step.duration}</span>
        <div className="ml-auto flex items-center gap-1">
          <button className="btn-ghost px-1.5 py-1" onClick={() => setCollapsed((c) => !c)} aria-expanded={!collapsed} aria-label={collapsed ? "Expand guide" : "Collapse guide"}>
            {collapsed ? <ChevronUp className="h-4 w-4" aria-hidden /> : <ChevronDown className="h-4 w-4" aria-hidden />}
          </button>
          <button className="btn-ghost px-1.5 py-1" onClick={() => { demo.exit(); navigate("/app"); }} aria-label="Exit demo"><X className="h-4 w-4" aria-hidden /></button>
        </div>
      </div>

      <nav className="flex gap-1 px-4 pt-2.5" aria-label={`Demo steps, step ${demo.step + 1} of ${STEPS.length}`}>
        {STEPS.map((s, i) => (
          <button key={s.title} onClick={() => goTo(i)} className={`h-1.5 flex-1 rounded-full ${i <= demo.step ? "bg-accent-600" : "bg-neutral-200"}`}
            aria-label={`Step ${i + 1}: ${s.title}`} aria-current={i === demo.step ? "step" : undefined} />
        ))}
      </nav>

      <div className="px-4 pb-3 pt-2.5">
        <h2 className="text-base font-semibold text-ink">{demo.step + 1}. {step.title}</h2>
        {!collapsed && (
          <>
            {missing.length > 0 && !loadingAccounts && (
              <p className="mt-2 rounded-md border border-warn-200 bg-warn-50 px-3 py-2 text-xs text-warn-700" role="status">
                {demo.accountsError ? "Couldn't load the demo accounts. " : "Some demo accounts aren't in the current dataset. "}
                This step falls back to the account list.
              </p>
            )}
            <ul className="mt-2 max-h-[34vh] space-y-1.5 overflow-y-auto text-sm text-ink-2 lg:max-h-none">
              {step.notice(demo.accounts).map((n) => <li key={n} className="flex gap-2"><span className="mt-2 h-1 w-1 shrink-0 rounded-full bg-ink-4" aria-hidden />{n}</li>)}
            </ul>
            <div className="mt-3">
              {here ? (
                <div className="flex items-center gap-1.5 text-xs font-medium text-accent-700"><Check className="h-3.5 w-3.5" aria-hidden /> You're on the {step.screen} screen</div>
              ) : (
                <button className="btn-primary w-full py-1.5" onClick={() => navigate(target)}>Open {step.screen}</button>
              )}
              {step.more && (
                <div className="mt-2 flex flex-wrap gap-x-3 gap-y-1">
                  {step.more(demo.accounts).map((l) => <Link key={l.label} to={l.to} className="text-xs font-medium text-accent-700 hover:underline">{l.label}</Link>)}
                </div>
              )}
            </div>
          </>
        )}
        <div className="mt-3 flex items-center gap-2 border-t border-line pt-2.5">
          <button className="btn-secondary px-2.5 py-1.5 text-xs" disabled={demo.step === 0} onClick={() => goTo(demo.step - 1)}><ArrowLeft className="h-3.5 w-3.5" aria-hidden /> Back</button>
          <button className="btn-ghost px-2 py-1.5 text-xs" onClick={() => goTo(0)}><RotateCcw className="h-3.5 w-3.5" aria-hidden /> Restart</button>
          {demo.step < STEPS.length - 1 ? (
            <button className="btn-primary ml-auto px-3 py-1.5 text-xs" onClick={() => goTo(demo.step + 1)}>Next: {STEPS[demo.step + 1].title} <ArrowRight className="h-3.5 w-3.5" aria-hidden /></button>
          ) : (
            <button className="btn-primary ml-auto px-3 py-1.5 text-xs" onClick={() => { demo.exit(); navigate("/app"); }}>Finish and explore GTMOS</button>
          )}
        </div>
      </div>
    </aside>
  );
}

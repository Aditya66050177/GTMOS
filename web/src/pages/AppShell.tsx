import { NavLink, Outlet, useLocation } from "react-router-dom";
import { useEffect, useState } from "react";
import { AlertTriangle, BarChart3, BookOpen, Columns3, FlaskConical, PlayCircle, Github, Inbox, KanbanSquare, LayoutDashboard, Menu, RotateCcw, Users, X } from "lucide-react";
import { DataTag, Logo } from "../components/ui";
import DemoGuide from "../components/DemoGuide";
import { useDemo } from "../demo/DemoContext";
import { dismissSandboxLoss, useSandboxLoss } from "../lib/sandboxStatus";
import { api } from "../lib/api";
import { SITE } from "../site";

const NAV_GROUPS = [
  {
    label: "Accounts",
    items: [
      { to: "/app", label: "Overview", icon: LayoutDashboard, end: true },
      { to: "/app/accounts", label: "Prioritized accounts", icon: Users },
      { to: "/app/compare", label: "Compare accounts", icon: Columns3 },
    ],
  },
  {
    label: "Execution",
    items: [
      { to: "/app/review", label: "Review queue", icon: Inbox },
      { to: "/app/pipeline", label: "Pipeline", icon: KanbanSquare },
    ],
  },
  {
    label: "Insight",
    items: [
      { to: "/app/analytics", label: "Analytics", icon: BarChart3 },
      { to: "/app/playground", label: "Scoring playground", icon: FlaskConical },
      { to: "/app/methodology", label: "Methodology", icon: BookOpen },
    ],
  },
];

export default function AppShell() {
  const [open, setOpen] = useState(false);
  const [resetting, setResetting] = useState(false);
  const [version, setVersion] = useState(0);
  const location = useLocation();

  const demo = useDemo();
  const sandboxLoss = useSandboxLoss();

  // Close the mobile menu on navigation; scroll to the top, or to #anchor once the
  // async content containing it has rendered (checked for up to ~3 s).
  useEffect(() => {
    setOpen(false);
    const id = location.hash.slice(1);
    if (!id) { window.scrollTo(0, 0); return; }
    let tries = 0;
    const timer = window.setInterval(() => {
      const el = document.getElementById(id);
      if (el || ++tries > 20) {
        window.clearInterval(timer);
        el?.scrollIntoView({ block: "start" });
      }
    }, 150);
    return () => window.clearInterval(timer);
  }, [location.pathname, location.hash, location.search]);

  async function reset() {
    if (!window.confirm("Reset your sandbox? Every draft, approval and edit you made will be undone.")) return;
    setResetting(true);
    try { await api.reset(); setVersion((v) => v + 1); } finally { setResetting(false); }
  }

  const nav = (
    <nav className="space-y-5" aria-label="Main">
      {NAV_GROUPS.map((group) => (
        <div key={group.label}>
          <div className="eyebrow px-2.5 pb-1.5">{group.label}</div>
          <div className="space-y-0.5">
            {group.items.map(({ to, label, icon: Icon, end }) => (
              <NavLink
                key={to} to={to} end={end}
                className={({ isActive }) =>
                  `flex items-center gap-2.5 rounded-md px-2.5 py-1.5 text-sm transition-colors ${
                    isActive ? "bg-accent-50 font-medium text-accent-700" : "text-ink-2 hover:bg-neutral-100 hover:text-ink"
                  }`
                }
              >
                <Icon className="h-4 w-4 shrink-0" aria-hidden /> {label}
              </NavLink>
            ))}
          </div>
        </div>
      ))}
    </nav>
  );

  const footer = (
    <div className="space-y-2.5 text-xs text-ink-3">
      {!demo.active && (
        <NavLink to="/demo" className="btn-primary w-full py-1.5 text-xs"><PlayCircle className="h-3.5 w-3.5" aria-hidden /> 5-minute guided demo</NavLink>
      )}
      <div className="rounded-md border border-line bg-subtle p-3 leading-relaxed">
        <div className="mb-1 font-semibold text-ink-2">Public sandbox</div>
        Synthetic companies and a simulated pipeline. AI runs offline. Your edits stay in this browser's sandbox and expire after about two hours.
      </div>
      <button onClick={reset} disabled={resetting} className="btn-secondary w-full py-1.5 text-xs">
        <RotateCcw className={`h-3.5 w-3.5 ${resetting ? "animate-spin" : ""}`} aria-hidden /> {resetting ? "Resetting…" : "Reset my sandbox"}
      </button>
      <a href={SITE.repoUrl} target="_blank" rel="noreferrer" className="flex items-center gap-2 px-1 hover:text-ink">
        <Github className="h-3.5 w-3.5" aria-hidden /> Source on GitHub
      </a>
    </div>
  );

  return (
    <div className={`min-h-screen lg:grid ${demo.active ? "lg:grid-cols-[232px_minmax(0,1fr)_360px]" : "lg:grid-cols-[232px_1fr]"}`}>
      <aside className="sticky top-0 hidden h-screen flex-col justify-between border-r border-line bg-surface px-3 py-4 lg:flex">
        <div className="space-y-6 overflow-y-auto">
          <div className="flex items-center justify-between px-2"><Logo /></div>
          {nav}
        </div>
        {footer}
      </aside>

      <header className="sticky top-0 z-30 flex h-14 items-center justify-between border-b border-line bg-surface px-4 lg:hidden">
        <Logo />
        <div className="flex items-center gap-2">
          <DataTag>Demo</DataTag>
          <button className="btn-secondary px-2.5 py-1.5" onClick={() => setOpen(true)} aria-label="Open menu" aria-expanded={open}>
            <Menu className="h-4 w-4" aria-hidden />
          </button>
        </div>
      </header>

      {open && (
        <div className="fixed inset-0 z-50 lg:hidden" role="dialog" aria-modal="true" aria-label="Menu">
          <div className="absolute inset-0 bg-ink/30" onClick={() => setOpen(false)} />
          <div className="absolute inset-y-0 left-0 flex w-72 max-w-[85vw] flex-col justify-between border-r border-line bg-surface p-4">
            <div className="space-y-6">
              <div className="flex items-center justify-between">
                <Logo />
                <button className="btn-ghost px-2.5 py-1.5" onClick={() => setOpen(false)} aria-label="Close menu"><X className="h-4 w-4" aria-hidden /></button>
              </div>
              {nav}
            </div>
            {footer}
          </div>
        </div>
      )}

      <main className="min-w-0">
        <div className="hidden h-12 items-center justify-end gap-2 border-b border-line bg-surface px-6 lg:flex">
          <DataTag>Demo · synthetic data · simulated pipeline</DataTag>
        </div>
        <div className={`mx-auto max-w-6xl px-4 py-5 sm:px-6 sm:py-6 ${demo.active ? "pb-[24rem] lg:pb-6" : ""}`} key={version}>
          {sandboxLoss && (
            <div role="status" aria-live="polite" className="mb-4 flex flex-wrap items-start gap-3 rounded-lg border border-warn-200 bg-warn-50 px-4 py-3">
              <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-warn-700" aria-hidden />
              <div className="min-w-0 flex-1 text-ink-2">
                <div className="font-semibold text-warn-700">Your earlier demo changes are no longer shown</div>
                <p className="mt-0.5">
                  {sandboxLoss.kind === "missing"
                    ? "This server has no record of your temporary sandbox. It may have expired (after about two hours), or a different server answered this request."
                    : "A new temporary sandbox was started for you because the previous one expired or is held by a different server."}
                  {" "}Draft approvals, edits and logged outreach from before are not shown anymore. They were never permanent:
                  demo changes live only in a temporary sandbox, nothing was sent, and shared demo data is unaffected.
                </p>
              </div>
              <button className="btn-secondary py-1.5 text-xs" onClick={dismissSandboxLoss}>Dismiss</button>
            </div>
          )}
          <Outlet />
        </div>
      </main>
      <DemoGuide />
    </div>
  );
}

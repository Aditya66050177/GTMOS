import { NavLink, Outlet, useLocation } from "react-router-dom";
import { useEffect, useState } from "react";
import { BarChart3, FlaskConical, Github, Inbox, KanbanSquare, LayoutDashboard, Menu, RotateCcw, Users, X } from "lucide-react";
import { Logo } from "../components/ui";
import { api } from "../lib/api";
import { SITE } from "../site";

const NAV = [
  { to: "/app", label: "Overview", icon: LayoutDashboard, end: true },
  { to: "/app/accounts", label: "Accounts", icon: Users },
  { to: "/app/review", label: "Review queue", icon: Inbox },
  { to: "/app/pipeline", label: "Pipeline", icon: KanbanSquare },
  { to: "/app/analytics", label: "Analytics", icon: BarChart3 },
  { to: "/app/playground", label: "Playground", icon: FlaskConical },
];

export default function AppShell() {
  const [open, setOpen] = useState(false);
  const [resetting, setResetting] = useState(false);
  const [version, setVersion] = useState(0);
  const location = useLocation();

  useEffect(() => { setOpen(false); window.scrollTo(0, 0); }, [location.pathname]);

  async function reset() {
    if (!window.confirm("Reset the sandbox? Every approval and stage change made here will be undone.")) return;
    setResetting(true);
    try { await api.reset(); setVersion((v) => v + 1); } finally { setResetting(false); }
  }

  const nav = (
    <nav className="flex flex-col gap-1">
      {NAV.map(({ to, label, icon: Icon, end }) => (
        <NavLink
          key={to} to={to} end={end}
          className={({ isActive }) =>
            `flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition ${
              isActive ? "bg-ink-800 text-mist-100" : "text-mist-400 hover:bg-ink-850 hover:text-mist-100"
            }`
          }
        >
          <Icon className="h-4 w-4" /> {label}
        </NavLink>
      ))}
    </nav>
  );

  const footer = (
    <div className="space-y-3 text-xs text-mist-500">
      <div className="rounded-xl border border-ink-700 bg-ink-850 p-3 leading-relaxed">
        <div className="mb-1 font-semibold text-mist-300">Public sandbox</div>
        Synthetic data, offline AI mode. Changes are shared with other visitors and reset on their own.
      </div>
      <button onClick={reset} disabled={resetting} className="btn-ghost w-full">
        <RotateCcw className={`h-4 w-4 ${resetting ? "animate-spin" : ""}`} /> {resetting ? "Resetting…" : "Reset sandbox"}
      </button>
      <a href={SITE.repoUrl} target="_blank" rel="noreferrer" className="flex items-center gap-2 px-1 hover:text-mist-100">
        <Github className="h-4 w-4" /> Source on GitHub
      </a>
    </div>
  );

  return (
    <div className="min-h-screen lg:grid lg:grid-cols-[248px_1fr]">
      <aside className="sticky top-0 hidden h-screen flex-col justify-between border-r border-ink-800 bg-ink-900/60 p-4 lg:flex">
        <div className="space-y-8">
          <div className="px-2 pt-1"><Logo /></div>
          {nav}
        </div>
        {footer}
      </aside>

      <header className="sticky top-0 z-30 flex h-14 items-center justify-between border-b border-ink-800 bg-ink-950/85 px-4 backdrop-blur lg:hidden">
        <Logo />
        <button className="btn-ghost px-3" onClick={() => setOpen(true)} aria-label="Open menu"><Menu className="h-4 w-4" /></button>
      </header>

      {open && (
        <div className="fixed inset-0 z-50 lg:hidden" role="dialog" aria-modal="true">
          <div className="absolute inset-0 bg-black/60" onClick={() => setOpen(false)} />
          <div className="absolute inset-y-0 left-0 flex w-72 max-w-[85vw] flex-col justify-between border-r border-ink-700 bg-ink-900 p-4">
            <div className="space-y-6">
              <div className="flex items-center justify-between px-1">
                <Logo />
                <button className="btn-ghost px-3" onClick={() => setOpen(false)} aria-label="Close menu"><X className="h-4 w-4" /></button>
              </div>
              {nav}
            </div>
            {footer}
          </div>
        </div>
      )}

      <main className="min-w-0 px-4 py-6 sm:px-8 sm:py-8">
        <div className="mx-auto max-w-6xl" key={version}>
          <Outlet />
        </div>
      </main>
    </div>
  );
}

import { Link } from "react-router-dom";
import { AlertCircle, Inbox, Loader2 } from "lucide-react";
import type { ReactNode } from "react";
import type { Action, Component, SignalItem, Tier } from "../lib/api";
import { ACTION_STYLE, TIER_STYLE, daysAgo, signalLabel } from "../lib/format";

export function Logo({ to = "/" }: { to?: string }) {
  return (
    <Link to={to} className="flex items-center gap-2" aria-label="GTMOS home">
      <svg viewBox="0 0 32 32" className="h-7 w-7" aria-hidden>
        <rect width="32" height="32" rx="6" fill="#0F766E" />
        <path d="M8 21V15M14 21V11M20 21V17M26 21V8" stroke="#fff" strokeWidth="3" strokeLinecap="round" />
      </svg>
      <span className="text-[15px] font-semibold tracking-tight text-ink">GTMOS</span>
    </Link>
  );
}

export function TierBadge({ tier }: { tier: Tier }) {
  return <span className={`badge ${TIER_STYLE[tier] ?? TIER_STYLE.Low}`}>{tier}</span>;
}

export function ActionBadge({ action }: { action: Action | null | undefined }) {
  if (!action) return <span className="text-ink-4">—</span>;
  return <span className={`badge tracking-wide ${ACTION_STYLE[action]}`}>{action}</span>;
}

/** Labels data provenance wherever numbers could be mistaken for real outcomes. */
export function DataTag({ children = "Synthetic data" }: { children?: ReactNode }) {
  return <span className="badge border-line-strong bg-subtle font-medium text-ink-3">{children}</span>;
}

/** Score out of 100 with a thin progress bar. Replaces the decorative ring. */
export function ScoreBlock({ score, tier, size = "lg" }: { score: number; tier?: Tier; size?: "lg" | "md" }) {
  return (
    <div className={size === "lg" ? "w-32" : "w-24"}>
      <div className="flex items-baseline gap-1">
        <span className={`num font-semibold tracking-tight text-ink ${size === "lg" ? "text-4xl" : "text-2xl"}`}>{score.toFixed(1)}</span>
        <span className="text-xs text-ink-4">/ 100</span>
      </div>
      <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-neutral-200" role="img" aria-label={`Score ${score.toFixed(1)} of 100`}>
        <div className="h-full rounded-full bg-accent-600" style={{ width: `${Math.min(score, 100)}%` }} />
      </div>
      {tier && <div className="mt-2"><TierBadge tier={tier} /></div>}
    </div>
  );
}

export function ComponentBars({ components }: { components: Component[] }) {
  return (
    <ul className="space-y-3">
      {components.map((c) => {
        const ratio = c.max_score ? c.score / c.max_score : 0;
        return (
          <li key={c.component}>
            <div className="mb-1 flex items-baseline justify-between gap-3">
              <span className="text-ink-2">{c.component}</span>
              <span className="num text-ink">
                {c.score.toFixed(1)}<span className="text-ink-4"> / {c.max_score}</span>
              </span>
            </div>
            <div className="h-1.5 overflow-hidden rounded-full bg-neutral-200" aria-hidden>
              <div className="h-full rounded-full bg-accent-600" style={{ width: `${ratio * 100}%` }} />
            </div>
          </li>
        );
      })}
    </ul>
  );
}

export function EvidenceCard({ signal }: { signal: SignalItem }) {
  const negative = signal.negative;
  return (
    <div className={`rounded-md border border-line border-l-[3px] bg-surface px-3.5 py-3 ${negative ? "border-l-danger-700" : "border-l-accent-600"}`}>
      <div className="flex flex-wrap items-baseline justify-between gap-x-3 gap-y-1">
        <span className={`text-sm font-semibold ${negative ? "text-danger-700" : "text-ink"}`}>
          {negative ? "Disqualifier: " : ""}{signalLabel(signal.type)}
        </span>
        <span className="num text-2xs text-ink-4">{Math.round((signal.confidence ?? 0) * 100)}% confidence</span>
      </div>
      <p className={`mt-1.5 leading-relaxed ${negative ? "text-ink-3" : "text-ink-2"}`}>
        {negative ? signal.description : <>“{signal.evidence}”</>}
      </p>
      <div className="mt-1.5 flex flex-wrap gap-x-3 text-2xs text-ink-4">
        <span>Source: {signal.source}</span>
        {signal.detected_at && <span>{daysAgo(signal.detected_at)}</span>}
      </div>
    </div>
  );
}

export function Kpi({ value, label, hint }: { value: ReactNode; label: string; hint?: string }) {
  return (
    <div className="panel px-4 py-3.5">
      <div className="text-xs font-medium text-ink-3">{label}</div>
      <div className="num mt-1 text-2xl font-semibold tracking-tight text-ink">{value}</div>
      {hint && <div className="mt-0.5 text-2xs text-ink-4">{hint}</div>}
    </div>
  );
}

export function Panel({ title, action, children, flush = false, className = "" }: {
  title?: ReactNode; action?: ReactNode; children: ReactNode; flush?: boolean; className?: string;
}) {
  return (
    <section className={`panel ${className}`}>
      {title && (
        <header className="panel-head">
          <h2 className="h-section">{title}</h2>
          {action}
        </header>
      )}
      <div className={flush ? "" : "panel-pad"}>{children}</div>
    </section>
  );
}

export function Loading({ label = "Loading" }: { label?: string }) {
  return (
    <div className="space-y-3 py-6" role="status" aria-live="polite">
      <div className="flex items-center gap-2 text-ink-3"><Loader2 className="h-4 w-4 animate-spin" aria-hidden /> {label}…</div>
      {[0, 1, 2].map((i) => <div key={i} className="h-10 animate-pulse rounded-md bg-neutral-200/70" />)}
    </div>
  );
}

export function EmptyState({ title, children }: { title: string; children?: ReactNode }) {
  return (
    <div className="flex flex-col items-center justify-center gap-1.5 rounded-lg border border-dashed border-line-strong bg-surface px-6 py-10 text-center">
      <Inbox className="h-5 w-5 text-ink-4" aria-hidden />
      <div className="font-medium text-ink-2">{title}</div>
      {children && <div className="max-w-md text-ink-3">{children}</div>}
    </div>
  );
}

export function ErrorBox({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div role="alert" className="flex flex-wrap items-start gap-3 rounded-lg border border-danger-200 bg-danger-50 px-4 py-3.5">
      <AlertCircle className="mt-0.5 h-4 w-4 text-danger-700" aria-hidden />
      <div className="min-w-0 flex-1">
        <div className="font-semibold text-danger-700">Couldn't load this view</div>
        <div className="mt-0.5 text-ink-2">{message}</div>
      </div>
      {onRetry && <button className="btn-secondary py-1.5" onClick={onRetry}>Retry</button>}
    </div>
  );
}

export function PageHeader({ eyebrow, title, description, children }: {
  eyebrow?: string; title: string; description?: ReactNode; children?: ReactNode;
}) {
  return (
    <div className="mb-5 flex flex-wrap items-end justify-between gap-3 border-b border-line pb-4">
      <div className="min-w-0">
        {eyebrow && <div className="eyebrow">{eyebrow}</div>}
        <h1 className="h-page mt-0.5">{title}</h1>
        {description && <p className="mt-1 max-w-3xl text-ink-3">{description}</p>}
      </div>
      {children && <div className="flex flex-wrap items-center gap-2">{children}</div>}
    </div>
  );
}

import { Link } from "react-router-dom";
import { AlertTriangle, Loader2, Quote, ShieldX } from "lucide-react";
import type { ReactNode } from "react";
import type { Action, Component, SignalItem, Tier } from "../lib/api";
import { ACTION_STYLE, TIER_STYLE, daysAgo, scoreColor, signalLabel } from "../lib/format";

export function Logo({ to = "/" }: { to?: string }) {
  return (
    <Link to={to} className="flex items-center gap-2.5" aria-label="GTMOS home">
      <svg viewBox="0 0 32 32" className="h-8 w-8" aria-hidden>
        <rect width="32" height="32" rx="8" fill="#11141B" stroke="#222836" />
        <path d="M7 20.5 12.5 15l4 4L25 10.5" fill="none" stroke="#4DFFAE" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" />
        <circle cx="25" cy="10.5" r="2.4" fill="#4DFFAE" />
      </svg>
      <span className="font-display text-lg font-semibold tracking-tight">GTMOS</span>
    </Link>
  );
}

export function TierBadge({ tier }: { tier: Tier }) {
  return <span className={`chip ${TIER_STYLE[tier] ?? TIER_STYLE.Low}`}>{tier}</span>;
}

export function ActionBadge({ action }: { action: Action | null | undefined }) {
  if (!action) return <span className="text-mist-500">—</span>;
  return <span className={`chip font-mono text-[10.5px] tracking-wide ${ACTION_STYLE[action]}`}>{action}</span>;
}

export function ScoreRing({ score, size = 112, label = "/ 100" }: { score: number; size?: number; label?: string }) {
  const r = (size - 12) / 2;
  const c = 2 * Math.PI * r;
  const color = scoreColor(score);
  return (
    <div className="relative shrink-0" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="-rotate-90">
        <circle cx={size / 2} cy={size / 2} r={r} stroke="#222836" strokeWidth="8" fill="none" />
        <circle
          cx={size / 2} cy={size / 2} r={r} stroke={color} strokeWidth="8" fill="none" strokeLinecap="round"
          strokeDasharray={c} strokeDashoffset={c * (1 - Math.min(score, 100) / 100)}
          style={{ transition: "stroke-dashoffset 0.8s ease" }}
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="font-display text-3xl font-semibold tabular-nums" style={{ color }}>{score.toFixed(1)}</span>
        <span className="text-[11px] text-mist-500">{label}</span>
      </div>
    </div>
  );
}

export function ComponentBars({ components }: { components: Component[] }) {
  return (
    <div className="space-y-3">
      {components.map((c) => {
        const ratio = c.max_score ? c.score / c.max_score : 0;
        return (
          <div key={c.component}>
            <div className="mb-1 flex items-baseline justify-between text-sm">
              <span className="text-mist-300">{c.component}</span>
              <span className="font-mono tabular-nums text-mist-100">
                {c.score.toFixed(1)}<span className="text-mist-500"> / {c.max_score}</span>
              </span>
            </div>
            <div className="h-2 overflow-hidden rounded-full bg-ink-800">
              <div
                className="h-full rounded-full transition-all duration-700"
                style={{ width: `${ratio * 100}%`, background: ratio >= 0.999 ? "#4DFFAE" : ratio > 0 ? "#5CC8FF" : "transparent" }}
              />
            </div>
          </div>
        );
      })}
    </div>
  );
}

export function EvidenceCard({ signal }: { signal: SignalItem }) {
  const negative = signal.negative;
  return (
    <div className={`rounded-xl border p-4 ${negative ? "border-rose-400/25 bg-rose-400/[0.04]" : "border-ink-700 bg-ink-850"}`}>
      <div className="mb-2 flex flex-wrap items-center gap-2">
        {negative ? <ShieldX className="h-4 w-4 text-rose-400" /> : <Quote className="h-4 w-4 text-signal-400" />}
        <span className={`text-sm font-semibold ${negative ? "text-rose-400" : "text-mist-100"}`}>{signalLabel(signal.type)}</span>
        <span className="ml-auto font-mono text-[11px] text-mist-500">
          {Math.round((signal.confidence ?? 0) * 100)}% conf.
        </span>
      </div>
      <p className={`text-sm leading-relaxed ${negative ? "font-mono text-mist-400" : "text-mist-300"}`}>
        {negative ? signal.description : <>“{signal.evidence}”</>}
      </p>
      <div className="mt-2 flex flex-wrap gap-x-3 text-[11px] text-mist-500">
        <span>Source: {signal.source}</span>
        {signal.detected_at && <span>{daysAgo(signal.detected_at)}</span>}
      </div>
    </div>
  );
}

export function Stat({ value, label, hint }: { value: ReactNode; label: string; hint?: string }) {
  return (
    <div className="card card-pad">
      <div className="font-display text-3xl font-semibold tabular-nums">{value}</div>
      <div className="mt-1 text-sm text-mist-400">{label}</div>
      {hint && <div className="mt-2 text-xs text-mist-500">{hint}</div>}
    </div>
  );
}

export function Loading({ label = "Loading" }: { label?: string }) {
  return (
    <div className="flex items-center gap-2 py-16 text-sm text-mist-400" role="status">
      <Loader2 className="h-4 w-4 animate-spin" /> {label}…
    </div>
  );
}

export function ErrorBox({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div className="card card-pad flex flex-wrap items-start gap-3 border-rose-400/30">
      <AlertTriangle className="mt-0.5 h-5 w-5 text-rose-400" />
      <div className="flex-1">
        <div className="font-semibold">Couldn't reach the GTMOS API</div>
        <div className="mt-1 text-sm text-mist-400">{message}</div>
      </div>
      {onRetry && <button className="btn-ghost" onClick={onRetry}>Retry</button>}
    </div>
  );
}

export function PageHeader({ eyebrow, title, children }: { eyebrow: string; title: string; children?: ReactNode }) {
  return (
    <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
      <div>
        <div className="eyebrow">{eyebrow}</div>
        <h1 className="h-display mt-1 text-2xl sm:text-3xl">{title}</h1>
      </div>
      {children}
    </div>
  );
}

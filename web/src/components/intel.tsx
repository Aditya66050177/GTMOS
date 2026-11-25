import { useMemo } from "react";
import type { Action, Contribution, EvidenceCounts, Explanation, PrioritizationRow, RejectedEvidence } from "../lib/api";
import { shortDate, signalLabel } from "../lib/format";

/* ------------------------------------------------------------------------- */
/* Fit / intent / total                                                       */
/* ------------------------------------------------------------------------- */

export const FIT_MEANING = "How closely the company matches the ideal customer profile.";
export const INTENT_MEANING = "How much credible, recent evidence suggests a reason to act now.";

export function Meter({ value, max, label }: { value: number | null; max: number; label: string }) {
  const v = value ?? 0;
  return (
    <div className="min-w-[72px]">
      <div className="num text-sm font-semibold text-ink">{value == null ? "—" : v.toFixed(1)}<span className="font-normal text-ink-4">/{max}</span></div>
      <div className="mt-1 h-1 rounded-full bg-neutral-200" role="img" aria-label={`${label} ${v.toFixed(1)} of ${max}`}>
        <div className="h-1 rounded-full bg-accent-600" style={{ width: `${Math.min(100, (v / max) * 100)}%` }} />
      </div>
    </div>
  );
}

export function ScoreTriplet({ fit, intent, total, tier }: { fit: number; intent: number; total: number; tier: string }) {
  const cells = [
    { label: "Fit", value: fit, max: 80, hint: FIT_MEANING },
    { label: "Intent", value: intent, max: 20, hint: INTENT_MEANING },
    { label: "Total", value: total, max: 100, hint: `${tier}. Tier comes from the total.` },
  ];
  return (
    <dl className="grid grid-cols-3 divide-x divide-line rounded-lg border border-line bg-surface">
      {cells.map((c) => (
        <div key={c.label} className="px-3 py-3 sm:px-4">
          <dt className="text-xs font-medium text-ink-3">{c.label}</dt>
          <dd>
            <span className="num text-2xl font-semibold tracking-tight">{c.value.toFixed(1)}</span>
            <span className="num text-xs text-ink-4"> / {c.max}</span>
            <div className="mt-1.5 h-1.5 rounded-full bg-neutral-200" aria-hidden>
              <div className="h-1.5 rounded-full bg-accent-600" style={{ width: `${Math.min(100, (c.value / c.max) * 100)}%` }} />
            </div>
            <p className="mt-1.5 hidden text-2xs leading-snug text-ink-4 sm:block">{c.hint}</p>
          </dd>
        </div>
      ))}
    </dl>
  );
}

/* ------------------------------------------------------------------------- */
/* Evidence status                                                            */
/* ------------------------------------------------------------------------- */

export const STATUS_STYLE: Record<string, string> = {
  current: "border-accent-100 bg-accent-50 text-accent-700",
  aging: "border-warn-200 bg-warn-50 text-warn-700",
  expired: "border-neutral-200 bg-neutral-100 text-ink-4",
  superseded: "border-line-strong bg-surface text-ink-4",
  disqualifier: "border-danger-200 bg-danger-50 text-danger-700",
  not_weighted: "border-line-strong bg-surface text-ink-4",
  rejected: "border-danger-200 bg-surface text-danger-700",
};

export function StatusBadge({ status }: { status: string }) {
  return <span className={`badge ${STATUS_STYLE[status] ?? STATUS_STYLE.superseded}`}>{status.replace("_", " ")}</span>;
}

export function EvidenceChips({ counts }: { counts: EvidenceCounts }) {
  const parts: [string, number][] = [
    ["current", counts.current], ["aging", counts.aging], ["expired", counts.expired], ["rejected", counts.rejected],
  ];
  const shown = parts.filter(([, n]) => n > 0);
  if (!shown.length) return <span className="text-xs text-ink-4">No evidence</span>;
  return (
    <span className="flex flex-wrap gap-1">
      {shown.map(([k, n]) => <span key={k} className={`badge ${STATUS_STYLE[k]}`}>{n} {k}</span>)}
    </span>
  );
}

/* ------------------------------------------------------------------------- */
/* Source sentence with the exact quote highlighted                           */
/* ------------------------------------------------------------------------- */

/** Highlights `quote` inside `sentence` only if it occurs there verbatim (case-insensitive).
 *  Never rewrites either string: if the quote can't be located, both are shown as stored. */
export function QuotedSentence({ sentence, quote }: { sentence: string | null; quote: string | null }) {
  if (!sentence) {
    return (
      <div>
        <p className="text-ink-2">{quote ? <>“{quote}”</> : <span className="text-ink-4">No quote stored.</span>}</p>
        <p className="mt-1 text-2xs text-ink-4">Stored quote. The full source sentence was not recorded for this signal.</p>
      </div>
    );
  }
  const at = quote ? sentence.toLowerCase().indexOf(quote.toLowerCase()) : -1;
  if (!quote || at < 0) {
    return (
      <div>
        <p className="text-ink-2">“{sentence}”</p>
        {quote && <p className="mt-1 text-2xs text-ink-4">Stored quote: “{quote}”</p>}
      </div>
    );
  }
  return (
    <p className="text-ink-2">
      “{sentence.slice(0, at)}
      <mark className="rounded-sm bg-accent-100 px-0.5 text-ink">{sentence.slice(at, at + quote.length)}</mark>
      {sentence.slice(at + quote.length)}”
    </p>
  );
}

/* ------------------------------------------------------------------------- */
/* Evidence inspector                                                         */
/* ------------------------------------------------------------------------- */

function Formula({ c }: { c: Contribution }) {
  const parts = [
    ["weight", c.weight.toFixed(0)], ["strength", c.strength.toFixed(2)], ["confidence", c.confidence.toFixed(2)], ["decay", c.decay.toFixed(1)],
  ];
  return (
    <div className="flex flex-wrap items-baseline gap-x-1.5 gap-y-1 font-mono text-xs text-ink-3">
      {parts.map(([k, v], i) => (
        <span key={k} className="whitespace-nowrap">{i > 0 && <span className="mr-1.5 text-ink-4">×</span>}<span className="text-ink">{v}</span> <span className="text-ink-4">{k}</span></span>
      ))}
      <span className="whitespace-nowrap"><span className="mr-1.5 text-ink-4">=</span><span className={`font-semibold ${c.points < 0 ? "text-danger-700" : c.points > 0 ? "text-accent-700" : "text-ink-4"}`}>{c.points > 0 ? "+" : ""}{c.points.toFixed(2)} pts</span></span>
    </div>
  );
}

const STATUS_NOTE: Record<string, (c: Contribution, e: Explanation) => string> = {
  current: (_c, e) => `Within ${e.intent.recency_rules.current_max_days} days: full weight.`,
  aging: (_c, e) => `${e.intent.recency_rules.current_max_days + 1}–${e.intent.recency_rules.aging_max_days} days old: counts at ${e.intent.recency_rules.aging_decay} weight.`,
  expired: (_c, e) => `Older than ${e.intent.recency_rules.aging_max_days} days: counts for nothing.`,
  superseded: () => "A newer signal of the same type is used instead; this one counts for nothing.",
  not_weighted: () => "This signal type has no weight in the scoring model.",
  disqualifier: () => "Penalty from the ICP rules, not from research notes.",
};

export function SignalRow({ c, e }: { c: Contribution; e: Explanation }) {
  return (
    <li className={`border-l-[3px] py-3 pl-3.5 pr-1 ${c.status === "disqualifier" ? "border-danger-700" : c.counted && c.points > 0 ? "border-accent-600" : "border-line-strong"}`}>
      <div className="flex flex-wrap items-center gap-2">
        <span className="font-semibold text-ink">{c.label}</span>
        <StatusBadge status={c.status} />
        <span className="text-2xs text-ink-4">{[c.source, c.detected_at ? `${shortDate(c.detected_at)} · ${c.days_old} days old` : null].filter(Boolean).join(" · ")}</span>
      </div>
      {c.status !== "disqualifier" ? <div className="mt-1.5"><QuotedSentence sentence={c.source_sentence} quote={c.quote} /></div>
        : <p className="mt-1.5 font-mono text-xs text-ink-3">{c.quote}</p>}
      <div className="mt-2"><Formula c={c} /></div>
      <p className="mt-1 text-2xs text-ink-4">
        {STATUS_NOTE[c.status]?.(c, e)}
        {c.why_it_matters && c.status !== "disqualifier" && <> Why it matters (product hypothesis): {c.why_it_matters}</>}
      </p>
    </li>
  );
}

export function RejectedRow({ r }: { r: RejectedEvidence }) {
  return (
    <li className="border-l-[3px] border-danger-200 py-3 pl-3.5 pr-1">
      <div className="flex flex-wrap items-center gap-2">
        <span className="font-semibold text-ink">{r.claimed_type ? signalLabel(r.claimed_type) : "Claim"}</span>
        <span className={`badge ${STATUS_STYLE.rejected}`}>rejected · {r.category}</span>
        <span className="text-2xs text-ink-4">{[r.source, r.date ? shortDate(r.date) : null, r.dataset === "demo_addition" ? "synthetic demo note" : null].filter(Boolean).join(" · ")}</span>
      </div>
      <p className="mt-1.5 text-ink-2">{r.sentence ? <>“{r.sentence}”</> : <span className="text-ink-4">Sentence not recorded.</span>}</p>
      <p className="mt-1 text-xs text-ink-3"><span className="font-medium">Why rejected:</span> {r.reason ?? "—"} · <span className="num font-semibold">0 pts</span></p>
    </li>
  );
}

export function EvidenceInspector({ e }: { e: Explanation }) {
  const signals = e.intent.buying_signals;
  return (
    <div className="space-y-5">
      <div>
        <div className="flex flex-wrap items-baseline justify-between gap-2">
          <h3 className="h-section">Buying signals ({signals.length})</h3>
          <span className="text-2xs text-ink-4">Newest signal of each type counts · decay: full ≤ {e.intent.recency_rules.current_max_days} d, ×{e.intent.recency_rules.aging_decay} ≤ {e.intent.recency_rules.aging_max_days} d, 0 after</span>
        </div>
        {signals.length ? (
          <ul className="mt-2 divide-y divide-line">{signals.map((c) => <SignalRow key={c.signal_id} c={c} e={e} />)}</ul>
        ) : (
          <p className="mt-2 rounded-md border border-dashed border-line-strong px-4 py-5 text-center text-ink-3">No verified buying signals for this account.</p>
        )}
      </div>

      {e.intent.disqualifiers.length > 0 && (
        <div>
          <h3 className="h-section">Disqualifier penalties ({e.intent.disqualifiers.length})</h3>
          <ul className="mt-2 divide-y divide-line">{e.intent.disqualifiers.map((c) => <SignalRow key={c.signal_id} c={c} e={e} />)}</ul>
        </div>
      )}

      <div>
        <h3 className="h-section">Rejected claims ({e.rejected_evidence.length})</h3>
        <p className="text-2xs text-ink-4">Read from the research notes but not counted: negated, unsupported (hearsay or not in the source) or ambiguous. Always 0 points.</p>
        {e.rejected_evidence.length ? (
          <ul className="mt-2 divide-y divide-line">{e.rejected_evidence.map((r, i) => <RejectedRow key={i} r={r} />)}</ul>
        ) : (
          <p className="mt-2 text-ink-3">No claims were rejected for this account.</p>
        )}
      </div>

      <div className="rounded-md border border-line bg-subtle px-3.5 py-3 text-xs text-ink-3">
        <div className="font-mono">
          intent = clamp(sum of points, 0, 20) = clamp({e.intent.raw_total.toFixed(2)}, 0, 20) = <span className="font-semibold text-ink">{e.intent.recomputed_score.toFixed(2)}</span>
        </div>
        <div className="mt-1">
          {e.intent.matches_stored_score
            ? "Matches the stored intent score used in the total."
            : <span className="text-danger-700">Does not match the stored intent ({e.intent.score.toFixed(2)}). The account may need re-scoring.</span>}
        </div>
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------------- */
/* Recommendation rule in plain English                                       */
/* ------------------------------------------------------------------------- */

// Plain-English restatements of the rows in RecommendationEngine's action table.
// The rule that fired (rule_id and its condition) always comes from the API.
export const RULE_PLAIN: Record<string, string> = {
  P1_INTENT_GE_10: "Strong fit (total of 90 or more) and at least 10 of 20 intent points: contact now.",
  P1_INTENT_LT_10: "Strong fit (total of 90 or more) but under 10 intent points: research for a recent trigger before reaching out.",
  P2_INTENT_GE_15: "Good fit (total 75–89.9) with at least 15 of 20 intent points: enough evidence to prioritize outreach.",
  P2_INTENT_5_TO_15: "Good fit (total 75–89.9) with some intent (5 to 15 points): nurture until a stronger trigger appears.",
  P2_INTENT_LT_5: "Good fit (total 75–89.9) but under 5 intent points: no credible reason to act now. Research first.",
  P3_INTENT_GE_10: "Moderate total (50–74.9) with at least 10 intent points: nurture.",
  P3_INTENT_LT_10: "Moderate total (50–74.9) with under 10 intent points: deprioritize for direct outreach.",
  LOW_ANY: "Total below 50: deprioritize, whatever the intent.",
};

export function RuleExplanation({ e }: { e: Explanation }) {
  const r = e.recommendation;
  return (
    <div className="space-y-3">
      <p className="text-ink">{RULE_PLAIN[r.rule_id] ?? r.reason}</p>
      <dl className="grid gap-x-4 gap-y-2 text-xs sm:grid-cols-[110px_1fr]">
        <dt className="text-ink-4">Tier rule</dt><dd className="font-mono text-ink-2">{e.total.rule}</dd>
        <dt className="text-ink-4">Action rule</dt><dd className="font-mono text-ink-2">{r.rule_id}: {r.rule}</dd>
        <dt className="text-ink-4">Persona</dt><dd className="text-ink-2">{r.suggested_persona ?? "—"}</dd>
        <dt className="text-ink-4">Angle</dt><dd className="text-ink-2">{r.suggested_angle ?? "—"}</dd>
      </dl>
      {(() => {
        const unmet = e.fit.components.flatMap((comp) => comp.reasons.filter((x) => !x.met).map((x) => ({ comp: comp.name, ...x })));
        if (!unmet.length && !e.intent.disqualifiers.length) return null;
        return (
          <div className="rounded-md border border-danger-200 bg-danger-50 px-3 py-2.5">
            <div className="text-xs font-semibold text-danger-700">Reasons for lower priority</div>
            <ul className="mt-1 space-y-0.5 text-xs text-ink-2">
              {unmet.map((u, i) => <li key={`u${i}`}><span className="font-medium">{u.comp}</span>: {u.text} <span className="num text-ink-3">({u.points.toFixed(1)} pts)</span></li>)}
              {e.intent.disqualifiers.map((c) => (
                <li key={c.signal_id}><span className="font-medium">Intent penalty, {c.label.toLowerCase()}</span>: <span className="font-mono">{c.quote}</span> <span className="num font-semibold text-danger-700">({c.points.toFixed(0)} pts)</span></li>
              ))}
            </ul>
            {e.intent.disqualifiers.length > 0 && (
              <p className="mt-1.5 text-2xs text-ink-3">The same size, industry or geography facts also lower fit, so these accounts are penalised in both fit and intent.</p>
            )}
          </div>
        );
      })()}
    </div>
  );
}

/* ------------------------------------------------------------------------- */
/* Fit x intent map                                                           */
/* ------------------------------------------------------------------------- */

// Validated (all-pairs, light) slots 1-3 of the reference palette; deprioritized accounts are grey context.
export const ACTION_GROUP: Record<Action, { key: string; label: string; color: string }> = {
  CONTACT: { key: "act", label: "Act now (Contact / Prioritize)", color: "#257de0" },
  PRIORITIZE: { key: "act", label: "Act now (Contact / Prioritize)", color: "#257de0" },
  NURTURE: { key: "nurture", label: "Nurture", color: "#f47230" },
  RESEARCH: { key: "research", label: "Research", color: "#00b894" },
  DEPRIORITIZE: { key: "drop", label: "Deprioritize", color: "#C4C9D2" },
};
const LEGEND = ["CONTACT", "NURTURE", "RESEARCH", "DEPRIORITIZE"] as Action[];

interface Point { fit: number; intent: number; rows: PrioritizationRow[]; color: string; key: string }

export function FitIntentMap({ rows, selected, onSelect }: {
  rows: PrioritizationRow[]; selected: string | null; onSelect: (key: string, rows: PrioritizationRow[]) => void;
}) {
  // Plot area is padded slightly beyond 0-80 / 0-20 so points on the edges don't cover the axis labels.
  const W = 720, H = 380, M = { l: 44, r: 16, t: 30, b: 40 };
  const X0 = -3, X1 = 83, Y0 = -1.6, Y1 = 21.2;
  const x = (f: number) => M.l + ((f - X0) / (X1 - X0)) * (W - M.l - M.r);
  const y = (i: number) => H - M.b - ((i - Y0) / (Y1 - Y0)) * (H - M.t - M.b);

  const points = useMemo<Point[]>(() => {
    const groups = new Map<string, PrioritizationRow[]>();
    for (const r of rows) {
      if (r.fit == null || r.intent == null || !r.action) continue;
      const k = `${r.fit.toFixed(1)}|${r.intent.toFixed(1)}|${ACTION_GROUP[r.action].key}`;
      groups.set(k, [...(groups.get(k) ?? []), r]);
    }
    return [...groups.entries()]
      .map(([key, rs]) => ({ key, fit: rs[0].fit!, intent: rs[0].intent!, rows: rs, color: ACTION_GROUP[rs[0].action!].color }))
      // Draw grey context first so coloured points sit on top.
      .sort((a, b) => (a.color === ACTION_GROUP.DEPRIORITIZE.color ? -1 : 0) - (b.color === ACTION_GROUP.DEPRIORITIZE.color ? -1 : 0));
  }, [rows]);

  // Tier boundaries are lines of constant total (fit + intent = 90, 75, 50).
  const tiers = [{ t: 90, label: "Priority 1 ≥ 90" }, { t: 75, label: "Priority 2 ≥ 75" }, { t: 50, label: "Priority 3 ≥ 50" }];

  return (
    <div>
      <svg viewBox={`0 0 ${W} ${H}`} className="w-full" role="group" aria-label="Accounts plotted by fit (horizontal, 0 to 80) and intent (vertical, 0 to 20)">
        {[0, 20, 40, 60, 80].map((f) => (
          <g key={`x${f}`}>
            <line x1={x(f)} x2={x(f)} y1={y(Y1)} y2={y(Y0)} stroke="#EAECF0" />
            <text x={x(f)} y={H - M.b + 16} textAnchor="middle" fontSize="11" fill="#667085">{f}</text>
          </g>
        ))}
        {[0, 5, 10, 15, 20].map((i) => (
          <g key={`y${i}`}>
            <line x1={x(X0)} x2={x(X1)} y1={y(i)} y2={y(i)} stroke="#EAECF0" />
            <text x={M.l - 8} y={y(i) + 4} textAnchor="end" fontSize="11" fill="#667085">{i}</text>
          </g>
        ))}
        <text x={(M.l + W - M.r) / 2} y={H - 6} textAnchor="middle" fontSize="11" fill="#475467" fontWeight="600">Fit (out of 80)</text>
        <text x={12} y={(M.t + H - M.b) / 2} textAnchor="middle" fontSize="11" fill="#475467" fontWeight="600" transform={`rotate(-90 12 ${(M.t + H - M.b) / 2})`}>Intent (out of 20)</text>
        {tiers.map(({ t, label }) => {
          const f0 = Math.max(0, t - 20), f1 = Math.min(80, t);
          return (
            <g key={t}>
              <line x1={x(f0)} y1={y(t - f0)} x2={x(f1)} y2={y(t - f1)} stroke="#98A2B3" strokeDasharray="4 4" />
              <text x={x(f0)} y={M.t - 10} textAnchor="middle" fontSize="10" fill="#667085">{label}</text>
              <line x1={x(f0)} x2={x(f0)} y1={M.t - 6} y2={y(t - f0)} stroke="#98A2B3" strokeDasharray="2 3" />
            </g>
          );
        })}
        {points.map((p) => {
          const n = p.rows.length;
          const r = Math.min(16, 5 + Math.sqrt(n) * 2.2);
          const isSel = selected === p.key;
          const names = p.rows.slice(0, 3).map((x) => x.name).join(", ") + (n > 3 ? ` and ${n - 3} more` : "");
          return (
            <g key={p.key} role="button" tabIndex={0} className="cursor-pointer outline-none"
              aria-label={`${n} account${n > 1 ? "s" : ""}: ${names}. Fit ${p.fit.toFixed(1)}, intent ${p.intent.toFixed(1)}.`}
              aria-pressed={isSel}
              onClick={() => onSelect(p.key, p.rows)}
              onKeyDown={(ev) => { if (ev.key === "Enter" || ev.key === " ") { ev.preventDefault(); onSelect(p.key, p.rows); } }}>
              <title>{`${names}\nFit ${p.fit.toFixed(1)} · Intent ${p.intent.toFixed(1)}`}</title>
              <circle cx={x(p.fit)} cy={y(p.intent)} r={r + 6} fill="transparent" />
              <circle cx={x(p.fit)} cy={y(p.intent)} r={r} fill={p.color} stroke={isSel ? "#101828" : "#FFFFFF"} strokeWidth={isSel ? 2.5 : 2} />
              {n > 1 && <text x={x(p.fit)} y={y(p.intent) + 3.5} textAnchor="middle" fontSize="10" fontWeight="600" fill="#101828" pointerEvents="none">{n}</text>}
            </g>
          );
        })}
      </svg>
      <ul className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-xs text-ink-3">
        {LEGEND.map((a) => (
          <li key={a} className="flex items-center gap-1.5"><span className="h-2.5 w-2.5 rounded-full" style={{ background: ACTION_GROUP[a].color }} aria-hidden />{ACTION_GROUP[a].label}</li>
        ))}
        <li className="flex items-center gap-1.5"><span className="h-px w-4 border-t border-dashed border-[#98A2B3]" aria-hidden />Tier boundary (fit + intent)</li>
        <li>Numbers show accounts sharing a point.</li>
      </ul>
    </div>
  );
}

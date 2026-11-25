import { Link } from "react-router-dom";
import { ArrowRight, Inbox } from "lucide-react";
import { api, type Tier } from "../lib/api";
import { useAsync } from "../lib/useAsync";
import { ErrorBox, Loading, PageHeader, Stat, TierBadge } from "../components/ui";

const TIER_COLOR: Record<Tier, string> = {
  "Priority 1": "#4DFFAE", "Priority 2": "#5CC8FF", "Priority 3": "#FFC857", Low: "#2E3546",
};
const STAGES = ["Research", "Contacted", "Replied", "Meeting", "Opportunity", "Won"];

export default function OverviewPage() {
  const { data, error, loading, reload } = useAsync(api.overview);
  if (loading && !data) return <Loading label="Warming up the sandbox" />;
  if (error || !data) return <ErrorBox message={error ?? "No data"} onRetry={reload} />;

  const total = Object.values(data.tiers).reduce((a, b) => a + b, 0) || 1;
  const maxStage = Math.max(...STAGES.map((s) => data.stages[s] ?? 0), 1);

  return (
    <div>
      <PageHeader eyebrow="Command center" title={data.product.name}>
        <span className="chip border-ink-600 bg-ink-850 font-mono text-mist-400">LLM mode: {data.llm_mode}</span>
      </PageHeader>
      <p className="-mt-3 mb-8 max-w-3xl text-sm text-mist-400">{data.product.description}</p>

      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <Stat value={data.counts.accounts} label="Accounts scored" />
        <Stat value={data.counts.signals} label="Verified signals" hint="each with a quoted source" />
        <Stat value={data.tiers["Priority 1"] + data.tiers["Priority 2"]} label="High-priority accounts" hint="Priority 1 and 2" />
        <Stat value={data.counts.won} label="Deals won" hint="from the 40-day simulation" />
      </div>

      {data.counts.pending_drafts > 0 && (
        <Link to="/app/review" className="card mt-4 flex items-center gap-4 border-signal-400/30 px-5 py-4 transition hover:border-signal-400/60">
          <Inbox className="h-5 w-5 text-signal-400" />
          <div className="flex-1 text-sm">
            <span className="font-semibold">{data.counts.pending_drafts} outreach drafts</span>
            <span className="text-mist-400"> are waiting for a human to approve, edit or reject.</span>
          </div>
          <ArrowRight className="h-4 w-4 text-mist-400" />
        </Link>
      )}

      <div className="mt-6 grid gap-4 lg:grid-cols-[1.2fr_0.8fr]">
        <div className="card card-pad">
          <div className="flex items-center justify-between">
            <h2 className="font-display text-lg font-semibold">Top accounts</h2>
            <Link to="/app/accounts" className="text-sm text-signal-400 hover:text-signal-300">All accounts</Link>
          </div>
          <ul className="mt-4 divide-y divide-ink-800">
            {data.top_accounts.map((a, i) => (
              <li key={a.id}>
                <Link to={`/app/accounts/${a.id}`} className="flex items-center gap-3 py-3 hover:text-signal-300">
                  <span className="w-5 font-mono text-xs text-mist-500">{i + 1}</span>
                  <span className="min-w-0 flex-1 truncate font-medium">{a.name}</span>
                  <span className="hidden text-xs text-mist-500 sm:inline">{a.stage}</span>
                  <TierBadge tier={a.tier} />
                  <span className="w-12 text-right font-mono tabular-nums">{a.total_score.toFixed(1)}</span>
                </Link>
              </li>
            ))}
          </ul>
        </div>

        <div className="card card-pad">
          <h2 className="font-display text-lg font-semibold">Tier distribution</h2>
          <div className="mt-4 flex h-3 overflow-hidden rounded-full bg-ink-800">
            {(Object.keys(data.tiers) as Tier[]).map((t) => (
              <div key={t} style={{ width: `${(data.tiers[t] / total) * 100}%`, background: TIER_COLOR[t] }} title={`${t}: ${data.tiers[t]}`} />
            ))}
          </div>
          <ul className="mt-4 space-y-2 text-sm">
            {(Object.keys(data.tiers) as Tier[]).map((t) => (
              <li key={t} className="flex items-center gap-2">
                <span className="h-2.5 w-2.5 rounded-sm" style={{ background: TIER_COLOR[t] }} />
                <span className="flex-1 text-mist-300">{t}</span>
                <span className="font-mono tabular-nums">{data.tiers[t]}</span>
              </li>
            ))}
          </ul>
          <h2 className="mt-8 font-display text-lg font-semibold">Pipeline</h2>
          <ul className="mt-3 space-y-2">
            {STAGES.map((s) => (
              <li key={s} className="grid grid-cols-[88px_1fr_32px] items-center gap-2 text-sm">
                <span className="text-mist-400">{s}</span>
                <div className="h-2 rounded-full bg-ink-800">
                  <div className="h-2 rounded-full bg-signal-500/80" style={{ width: `${((data.stages[s] ?? 0) / maxStage) * 100}%` }} />
                </div>
                <span className="text-right font-mono tabular-nums">{data.stages[s] ?? 0}</span>
              </li>
            ))}
          </ul>
        </div>
      </div>

      {data.icp && (
        <div className="card card-pad mt-4">
          <h2 className="font-display text-lg font-semibold">Ideal customer profile</h2>
          <p className="mt-1 text-sm text-mist-400">Generated from the product description, validated against a Pydantic schema before any engine used it.</p>
          <div className="mt-5 grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
            {[
              ["Industries", data.icp.industries],
              ["Company size", [`${data.icp.company_size_min}–${data.icp.company_size_max} employees`]],
              ["Geographies", data.icp.geographies],
              ["Buyer roles", data.icp.buyer_roles],
              ["Technologies", data.icp.technologies],
              ["Exclusions", data.icp.exclusions],
            ].map(([label, values]) => (
              <div key={label as string}>
                <div className="label">{label as string}</div>
                <div className="flex flex-wrap gap-1.5">
                  {(values as string[]).map((v) => <span key={v} className="chip border-ink-600 bg-ink-850 text-mist-300">{v}</span>)}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

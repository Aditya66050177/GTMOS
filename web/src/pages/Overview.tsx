import { Link } from "react-router-dom";
import { ArrowRight } from "lucide-react";
import { api, type Tier } from "../lib/api";
import { useAsync } from "../lib/useAsync";
import { DataTag, ErrorBox, Kpi, Loading, PageHeader, Panel, TierBadge } from "../components/ui";
import { TIER_FILL } from "../lib/format";

const TIERS: Tier[] = ["Priority 1", "Priority 2", "Priority 3", "Low"];
const STAGES = ["Research", "Contacted", "Replied", "Meeting", "Opportunity", "Won"];

export default function OverviewPage() {
  const { data, error, loading, reload } = useAsync(api.overview);
  if (loading && !data) return <Loading label="Warming up the sandbox" />;
  if (error || !data) return <ErrorBox message={error ?? "No data returned."} onRetry={reload} />;

  const total = TIERS.reduce((sum, t) => sum + (data.tiers[t] ?? 0), 0) || 1;
  const maxStage = Math.max(...STAGES.map((s) => data.stages[s] ?? 0), 1);
  const highPriority = (data.tiers["Priority 1"] ?? 0) + (data.tiers["Priority 2"] ?? 0);

  return (
    <div className="space-y-4">
      <PageHeader eyebrow="Command center" title={data.product.name} description={data.product.description}>
        <span className="badge border-line-strong bg-subtle font-medium text-ink-3">LLM mode: {data.llm_mode}</span>
      </PageHeader>

      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <Kpi value={data.counts.accounts} label="Accounts scored" hint="out of 100 points each" />
        <Kpi value={highPriority} label="Priority 1 and 2" hint="worth sales attention" />
        <Kpi value={data.counts.signals} label="Verified buying signals" hint="each quotes its source" />
        <Kpi value={data.counts.pending_drafts} label="Drafts awaiting review" hint="none sent automatically" />
      </div>

      {data.counts.pending_drafts > 0 && (
        <Link to="/app/review" className="panel flex items-center gap-3 px-4 py-3 transition-colors hover:border-accent-600">
          <span className="h-2 w-2 shrink-0 rounded-full bg-accent-600" aria-hidden />
          <span className="flex-1 text-ink-2">
            <span className="font-semibold text-ink">{data.counts.pending_drafts} outreach drafts</span> are waiting for a person to approve, edit or reject.
          </span>
          <ArrowRight className="h-4 w-4 text-ink-4" aria-hidden />
        </Link>
      )}

      <div className="grid gap-4 lg:grid-cols-[1.25fr_0.75fr]">
        <Panel title="Top-scored accounts" flush action={<Link to="/app/accounts" className="text-sm font-medium text-accent-700 hover:underline">All accounts</Link>}>
          <div className="overflow-x-auto" tabIndex={0}>
            <table className="tbl">
              <thead>
                <tr><th className="w-8">#</th><th>Account</th><th className="hidden sm:table-cell">Stage</th><th>Tier</th><th className="r">Score</th></tr>
              </thead>
              <tbody>
                {data.top_accounts.map((a, i) => (
                  <tr key={a.id} className="hover:bg-subtle">
                    <td className="num text-ink-4">{i + 1}</td>
                    <td><Link to={`/app/accounts/${a.id}`} className="font-medium text-ink hover:text-accent-700 hover:underline">{a.name}</Link></td>
                    <td className="hidden text-ink-3 sm:table-cell">{a.stage}</td>
                    <td><TierBadge tier={a.tier} /></td>
                    <td className="r font-medium">{a.total_score.toFixed(1)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Panel>

        <div className="space-y-4">
          <Panel title="Tier distribution">
            <div className="flex h-2.5 gap-0.5 overflow-hidden rounded-sm" role="img"
              aria-label={TIERS.map((t) => `${t}: ${data.tiers[t] ?? 0}`).join(", ")}>
              {TIERS.map((t) => (data.tiers[t] ?? 0) > 0 && (
                <div key={t} style={{ width: `${((data.tiers[t] ?? 0) / total) * 100}%`, background: TIER_FILL[t] }} title={`${t}: ${data.tiers[t]}`} />
              ))}
            </div>
            <table className="mt-3 w-full">
              <tbody>
                {TIERS.map((t) => (
                  <tr key={t}>
                    <td className="py-1"><span className="inline-flex items-center gap-2 text-ink-2"><span className="h-2.5 w-2.5 rounded-sm" style={{ background: TIER_FILL[t] }} aria-hidden />{t}</span></td>
                    <td className="num py-1 text-right font-medium">{data.tiers[t] ?? 0}</td>
                    <td className="num w-14 py-1 text-right text-ink-4">{Math.round(((data.tiers[t] ?? 0) / total) * 100)}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Panel>

          <Panel title="Pipeline by stage" action={<DataTag>Simulated</DataTag>}>
            <ul className="space-y-2">
              {STAGES.map((s) => (
                <li key={s} className="grid grid-cols-[92px_1fr_32px] items-center gap-2">
                  <span className="text-ink-3">{s}</span>
                  <div className="h-2 rounded-sm bg-neutral-100">
                    <div className="h-2 rounded-sm bg-accent-600" style={{ width: `${((data.stages[s] ?? 0) / maxStage) * 100}%` }} />
                  </div>
                  <span className="num text-right font-medium">{data.stages[s] ?? 0}</span>
                </li>
              ))}
            </ul>
          </Panel>
        </div>
      </div>

      {data.icp && (
        <Panel title="Ideal customer profile" action={<span className="text-2xs text-ink-4">Generated, then schema-validated</span>}>
          <dl className="grid gap-x-6 gap-y-4 sm:grid-cols-2 lg:grid-cols-3">
            {([
              ["Industries", data.icp.industries],
              ["Company size", [`${data.icp.company_size_min}–${data.icp.company_size_max} employees`]],
              ["Geographies", data.icp.geographies],
              ["Buyer roles", data.icp.buyer_roles],
              ["Technologies", data.icp.technologies],
              ["Exclusions", data.icp.exclusions],
            ] as [string, string[]][]).map(([label, values]) => (
              <div key={label}>
                <dt className="label">{label}</dt>
                <dd className="flex flex-wrap gap-1">
                  {values.map((v) => <span key={v} className="badge border-line bg-subtle font-medium text-ink-2">{v}</span>)}
                </dd>
              </div>
            ))}
          </dl>
        </Panel>
      )}
    </div>
  );
}

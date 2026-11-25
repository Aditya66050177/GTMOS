import { Link } from "react-router-dom";
import { api } from "../lib/api";
import { useAsync } from "../lib/useAsync";
import { DataTag, ErrorBox, Loading, PageHeader, TierBadge } from "../components/ui";

const ORDER = ["Research", "Contacted", "Replied", "Meeting", "Opportunity", "Won", "Lost"];
const money = (n: number) => (n >= 1000 ? `$${Math.round(n / 1000)}k` : `$${n}`);

export default function PipelinePage() {
  const { data, error, loading, reload } = useAsync(api.pipeline);
  if (loading && !data) return <Loading />;
  if (error || !data) return <ErrorBox message={error ?? "No data returned."} onRetry={reload} />;

  return (
    <div>
      <PageHeader eyebrow="Lightweight CRM" title="Pipeline"
        description="Stage changes write a timestamped activity, and accounts only move through valid transitions. The 40 days of activity here are simulated.">
        <DataTag>Simulated pipeline</DataTag>
        <span className="num text-xs text-ink-4">{data.total_accounts} accounts</span>
      </PageHeader>
      <div className="-mx-4 overflow-x-auto px-4 pb-2 sm:mx-0 sm:px-0">
        <div className="flex gap-3" style={{ minWidth: ORDER.length * 228 }}>
          {ORDER.map((stage) => {
            const group = data.stages[stage];
            const accounts = [...(group?.accounts ?? [])].sort((a, b) => b.total_score - a.total_score);
            const value = accounts.reduce((s, a) => s + (a.deal_value ?? 0), 0);
            return (
              <section key={stage} className="flex w-[216px] shrink-0 flex-col rounded-lg border border-line bg-subtle" aria-label={`${stage} stage`}>
                <header className="border-b border-line bg-surface px-3 py-2.5">
                  <div className="flex items-center justify-between">
                    <h2 className={`text-sm font-semibold ${stage === "Lost" ? "text-ink-3" : "text-ink"}`}>{stage}</h2>
                    <span className="num rounded bg-neutral-100 px-1.5 text-xs font-medium text-ink-3">{group?.count ?? 0}</span>
                  </div>
                  <div className="num mt-0.5 h-4 text-2xs text-ink-4">{value > 0 ? `${money(value)} simulated deal value` : ""}</div>
                </header>
                <ul className="max-h-[560px] space-y-1.5 overflow-y-auto p-2">
                  {accounts.slice(0, 40).map((a) => (
                    <li key={a.id}>
                      <Link to={`/app/accounts/${a.id}`} className="block rounded-md border border-line bg-surface px-2.5 py-2 shadow-card transition-colors hover:border-accent-600">
                        <div className="truncate font-medium text-ink">{a.name}</div>
                        <div className="mt-1.5 flex items-center justify-between">
                          <TierBadge tier={a.tier} />
                          <span className="num text-xs font-medium text-ink-2">{a.total_score.toFixed(1)}</span>
                        </div>
                      </Link>
                    </li>
                  ))}
                  {accounts.length > 40 && <li className="px-1 py-1 text-2xs text-ink-4">+{accounts.length - 40} more</li>}
                  {accounts.length === 0 && <li className="px-1 py-3 text-center text-xs text-ink-4">No accounts</li>}
                </ul>
              </section>
            );
          })}
        </div>
      </div>
    </div>
  );
}

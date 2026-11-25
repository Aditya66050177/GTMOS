import { Link } from "react-router-dom";
import { api } from "../lib/api";
import { useAsync } from "../lib/useAsync";
import { ErrorBox, Loading, PageHeader, TierBadge } from "../components/ui";

const ORDER = ["Research", "Contacted", "Replied", "Meeting", "Opportunity", "Won", "Lost"];
const money = (n: number) => n >= 1000 ? `$${Math.round(n / 1000)}k` : `$${n}`;

export default function PipelinePage() {
  const { data, error, loading, reload } = useAsync(api.pipeline);
  if (loading && !data) return <Loading />;
  if (error || !data) return <ErrorBox message={error ?? "No data"} onRetry={reload} />;

  return (
    <div>
      <PageHeader eyebrow="Lightweight CRM" title="Pipeline">
        <span className="text-sm text-mist-400">{data.total_accounts} accounts</span>
      </PageHeader>
      <p className="-mt-3 mb-6 max-w-3xl text-sm text-mist-400">
        Forty days of simulated activity. Every stage change writes a timestamped activity, and accounts only move forward
        through valid transitions.
      </p>
      <div className="-mx-4 overflow-x-auto px-4 pb-4 sm:mx-0 sm:px-0">
        <div className="flex gap-3" style={{ minWidth: ORDER.length * 236 }}>
          {ORDER.map((stage) => {
            const group = data.stages[stage];
            const accounts = [...(group?.accounts ?? [])].sort((a, b) => b.total_score - a.total_score);
            const value = accounts.reduce((s, a) => s + (a.deal_value ?? 0), 0);
            return (
              <section key={stage} className="flex w-[224px] shrink-0 flex-col rounded-2xl border border-ink-700 bg-ink-900/70">
                <header className="border-b border-ink-800 px-4 py-3">
                  <div className="flex items-center justify-between">
                    <h2 className={`text-sm font-semibold ${stage === "Won" ? "text-signal-300" : stage === "Lost" ? "text-rose-400" : ""}`}>{stage}</h2>
                    <span className="font-mono text-xs text-mist-500">{group?.count ?? 0}</span>
                  </div>
                  {value > 0 && <div className="mt-0.5 font-mono text-[11px] text-mist-500">{money(value)} in deals</div>}
                </header>
                <ul className="max-h-[560px] space-y-2 overflow-y-auto p-2">
                  {accounts.slice(0, 40).map((a) => (
                    <li key={a.id}>
                      <Link to={`/app/accounts/${a.id}`} className="block rounded-xl border border-ink-700 bg-ink-850 p-3 transition hover:border-ink-600">
                        <div className="truncate text-sm font-medium">{a.name}</div>
                        <div className="mt-2 flex items-center justify-between">
                          <TierBadge tier={a.tier} />
                          <span className="font-mono text-xs tabular-nums text-mist-400">{a.total_score.toFixed(1)}</span>
                        </div>
                      </Link>
                    </li>
                  ))}
                  {accounts.length > 40 && <li className="px-2 py-1 text-xs text-mist-500">+{accounts.length - 40} more</li>}
                </ul>
              </section>
            );
          })}
        </div>
      </div>
    </div>
  );
}

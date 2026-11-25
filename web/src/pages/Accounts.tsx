import { useMemo, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { Search } from "lucide-react";
import { api, type AccountRow, type Tier } from "../lib/api";
import { useAsync } from "../lib/useAsync";
import { ActionBadge, ErrorBox, Loading, PageHeader, TierBadge } from "../components/ui";
import { signalLabel } from "../lib/format";

const TIERS: (Tier | "All")[] = ["All", "Priority 1", "Priority 2", "Priority 3", "Low"];
type SortKey = "total_score" | "intent_score" | "name";

export default function AccountsPage() {
  const { data, error, loading, reload } = useAsync(api.accounts);
  const [params, setParams] = useSearchParams();
  const [sort, setSort] = useState<SortKey>("total_score");
  const navigate = useNavigate();
  const q = params.get("q") ?? "";
  const tier = (params.get("tier") as Tier | null) ?? "All";

  const rows = useMemo(() => {
    if (!data) return [];
    const needle = q.trim().toLowerCase();
    const filtered = data.filter(
      (r) => (tier === "All" || r.tier === tier) &&
        (!needle || `${r.name} ${r.industry ?? ""} ${r.country ?? ""}`.toLowerCase().includes(needle)),
    );
    return [...filtered].sort((a, b) =>
      sort === "name" ? a.name.localeCompare(b.name) : (b[sort] as number) - (a[sort] as number),
    );
  }, [data, q, tier, sort]);

  function update(key: string, value: string) {
    const next = new URLSearchParams(params);
    if (value && value !== "All") next.set(key, value); else next.delete(key);
    setParams(next, { replace: true });
  }

  if (loading && !data) return <Loading />;
  if (error || !data) return <ErrorBox message={error ?? "No data"} onRetry={reload} />;

  return (
    <div>
      <PageHeader eyebrow="Ranked target list" title="Accounts">
        <span className="text-sm text-mist-400">{rows.length} of {data.length}</span>
      </PageHeader>

      <div className="mb-4 flex flex-col gap-3 sm:flex-row">
        <label className="relative flex-1">
          <span className="sr-only">Search accounts</span>
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-mist-500" />
          <input className="input pl-9" placeholder="Search name, industry, country" value={q} onChange={(e) => update("q", e.target.value)} />
        </label>
        <div className="flex gap-1 overflow-x-auto rounded-xl border border-ink-700 bg-ink-900 p-1">
          {TIERS.map((t) => (
            <button
              key={t} onClick={() => update("tier", t)}
              className={`whitespace-nowrap rounded-lg px-3 py-1.5 text-xs font-medium ${tier === t ? "bg-ink-700 text-mist-100" : "text-mist-400 hover:text-mist-100"}`}
            >{t}</button>
          ))}
        </div>
        <select className="input sm:w-44" value={sort} onChange={(e) => setSort(e.target.value as SortKey)} aria-label="Sort by">
          <option value="total_score">Sort: score</option>
          <option value="intent_score">Sort: intent</option>
          <option value="name">Sort: name</option>
        </select>
      </div>

      {/* Desktop table */}
      <div className="card hidden overflow-hidden md:block">
        <table className="w-full text-sm">
          <thead className="border-b border-ink-800 text-left text-xs text-mist-500">
            <tr>
              <th className="px-4 py-3 font-medium">Account</th>
              <th className="px-4 py-3 font-medium">Tier</th>
              <th className="px-4 py-3 text-right font-medium">Score</th>
              <th className="px-4 py-3 text-right font-medium">Intent</th>
              <th className="px-4 py-3 font-medium">Top signal</th>
              <th className="px-4 py-3 font-medium">Next action</th>
              <th className="px-4 py-3 font-medium">Stage</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-ink-800">
            {rows.map((r) => (
              <tr key={r.id} className="cursor-pointer hover:bg-ink-850" onClick={() => navigate(`/app/accounts/${r.id}`)}>
                <td className="px-4 py-3">
                  <Link to={`/app/accounts/${r.id}`} className="font-medium hover:text-signal-300" onClick={(e) => e.stopPropagation()}>{r.name}</Link>
                  <div className="text-xs text-mist-500">{r.industry} · {r.employee_count} · {r.country}</div>
                </td>
                <td className="px-4 py-3"><TierBadge tier={r.tier} /></td>
                <td className="px-4 py-3 text-right font-mono tabular-nums">{r.total_score.toFixed(1)}</td>
                <td className="px-4 py-3 text-right font-mono tabular-nums text-mist-300">{r.intent_score.toFixed(1)}</td>
                <td className="px-4 py-3 text-mist-300">{signalLabel(r.top_signal)}</td>
                <td className="px-4 py-3"><ActionBadge action={r.action} /></td>
                <td className="px-4 py-3 text-mist-400">{r.stage}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Mobile cards */}
      <ul className="space-y-2 md:hidden">
        {rows.map((r: AccountRow) => (
          <li key={r.id}>
            <Link to={`/app/accounts/${r.id}`} className="card flex items-center gap-3 px-4 py-3">
              <div className="min-w-0 flex-1">
                <div className="truncate font-medium">{r.name}</div>
                <div className="mt-1 flex flex-wrap items-center gap-1.5"><TierBadge tier={r.tier} /><ActionBadge action={r.action} /></div>
              </div>
              <div className="font-mono text-lg tabular-nums">{r.total_score.toFixed(1)}</div>
            </Link>
          </li>
        ))}
      </ul>
      {rows.length === 0 && <div className="py-12 text-center text-sm text-mist-400">No accounts match those filters.</div>}
    </div>
  );
}

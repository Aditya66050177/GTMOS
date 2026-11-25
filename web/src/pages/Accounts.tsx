import { useMemo, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { Search } from "lucide-react";
import { api, type Tier } from "../lib/api";
import { useAsync } from "../lib/useAsync";
import { ActionBadge, EmptyState, ErrorBox, Loading, PageHeader, TierBadge } from "../components/ui";
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

  const counts = useMemo(() => {
    const c: Record<string, number> = { All: data?.length ?? 0 };
    for (const r of data ?? []) c[r.tier] = (c[r.tier] ?? 0) + 1;
    return c;
  }, [data]);

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
  if (error || !data) return <ErrorBox message={error ?? "No data returned."} onRetry={reload} />;

  return (
    <div>
      <PageHeader eyebrow="Ranked target list" title="Prioritized accounts"
        description="Every account scored out of 100 by deterministic rules. Open one to see exactly why." />

      <div className="mb-3 flex flex-col gap-2 lg:flex-row lg:items-center">
        <label className="relative lg:w-72">
          <span className="sr-only">Search accounts</span>
          <Search className="pointer-events-none absolute left-2.5 top-1/2 h-4 w-4 -translate-y-1/2 text-ink-4" aria-hidden />
          <input className="input pl-8" placeholder="Search name, industry, country" value={q} onChange={(e) => update("q", e.target.value)} />
        </label>
        <div className="segmented overflow-x-auto" role="group" aria-label="Filter by tier">
          {TIERS.map((t) => (
            <button key={t} type="button" aria-pressed={tier === t} onClick={() => update("tier", t)} className="whitespace-nowrap">
              {t} <span className="num text-ink-4">{counts[t] ?? 0}</span>
            </button>
          ))}
        </div>
        <div className="flex items-center gap-2 lg:ml-auto">
          <label htmlFor="sort" className="text-xs text-ink-3">Sort</label>
          <select id="sort" className="input w-36 py-1.5" value={sort} onChange={(e) => setSort(e.target.value as SortKey)}>
            <option value="total_score">Score</option>
            <option value="intent_score">Intent</option>
            <option value="name">Name</option>
          </select>
          <span className="num whitespace-nowrap text-xs text-ink-4">{rows.length} of {data.length}</span>
        </div>
      </div>

      {rows.length === 0 ? (
        <EmptyState title="No accounts match these filters">Clear the search or choose another tier.</EmptyState>
      ) : (
        <>
          <div className="panel hidden max-h-[calc(100vh-15rem)] overflow-auto md:block">
            <table className="tbl">
              <thead>
                <tr>
                  <th>Account</th>
                  <th>Tier</th>
                  <th className="r">Score</th>
                  <th className="r">Intent /20</th>
                  <th>Top signal</th>
                  <th>Next action</th>
                  <th>Stage</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((r) => (
                  <tr key={r.id} className="cursor-pointer hover:bg-subtle" onClick={() => navigate(`/app/accounts/${r.id}`)}>
                    <td>
                      <Link to={`/app/accounts/${r.id}`} className="font-medium text-ink hover:text-accent-700 hover:underline" onClick={(e) => e.stopPropagation()}>{r.name}</Link>
                      <div className="text-2xs text-ink-4">{r.industry} · {r.employee_count} employees · {r.country}</div>
                    </td>
                    <td><TierBadge tier={r.tier} /></td>
                    <td className="r font-semibold">{r.total_score.toFixed(1)}</td>
                    <td className={`r ${r.intent_score > 0 ? "text-ink" : "text-ink-4"}`}>{r.intent_score.toFixed(1)}</td>
                    <td className={r.top_signal ? "text-ink-2" : "text-ink-4"}>{signalLabel(r.top_signal)}</td>
                    <td><ActionBadge action={r.action} /></td>
                    <td className="text-ink-3">{r.stage}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <ul className="panel divide-y divide-line md:hidden">
            {rows.map((r) => (
              <li key={r.id}>
                <Link to={`/app/accounts/${r.id}`} className="flex items-center gap-3 px-4 py-3 hover:bg-subtle">
                  <div className="min-w-0 flex-1">
                    <div className="truncate font-medium text-ink">{r.name}</div>
                    <div className="mt-1 flex flex-wrap items-center gap-1.5"><TierBadge tier={r.tier} /><ActionBadge action={r.action} /></div>
                  </div>
                  <div className="text-right">
                    <div className="num text-lg font-semibold">{r.total_score.toFixed(1)}</div>
                    <div className="num text-2xs text-ink-4">intent {r.intent_score.toFixed(1)}</div>
                  </div>
                </Link>
              </li>
            ))}
          </ul>
        </>
      )}
    </div>
  );
}

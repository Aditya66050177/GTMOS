import { useMemo, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { Info, Search } from "lucide-react";
import { api, type Action, type PrioritizationRow, type Tier } from "../lib/api";
import { useAsync } from "../lib/useAsync";
import { ActionBadge, EmptyState, ErrorBox, Loading, PageHeader, Panel, TierBadge } from "../components/ui";
import { EvidenceChips, FIT_MEANING, FitIntentMap, INTENT_MEANING, Meter } from "../components/intel";

const TIERS: (Tier | "All")[] = ["All", "Priority 1", "Priority 2", "Priority 3", "Low"];
const ACTIONS: (Action | "All")[] = ["All", "CONTACT", "PRIORITIZE", "NURTURE", "RESEARCH", "DEPRIORITIZE"];
const EVIDENCE = [
  { key: "all", label: "Any evidence" },
  { key: "current", label: "Has a current signal" },
  { key: "aging", label: "Only aging or expired signals" },
  { key: "rejected", label: "Has rejected claims" },
  { key: "none", label: "No signals" },
] as const;
type SortKey = "total" | "fit" | "intent" | "name";

function matchesEvidence(r: PrioritizationRow, key: string) {
  const e = r.evidence;
  switch (key) {
    case "current": return e.current > 0;
    case "aging": return e.current === 0 && e.aging + e.expired > 0;
    case "rejected": return e.rejected > 0;
    case "none": return e.current + e.aging + e.expired + e.superseded === 0;
    default: return true;
  }
}

export default function AccountsPage() {
  const { data, error, loading, reload } = useAsync(api.prioritization);
  const [params, setParams] = useSearchParams();
  const [sort, setSort] = useState<SortKey>("total");
  const [selected, setSelected] = useState<{ key: string; rows: PrioritizationRow[] } | null>(null);
  const navigate = useNavigate();
  const q = params.get("q") ?? "";
  const tier = (params.get("tier") as Tier | null) ?? "All";
  const action = (params.get("action") as Action | null) ?? "All";
  const evidence = params.get("evidence") ?? "all";
  const view = params.get("view") === "map" ? "map" : "table";

  const rows = useMemo(() => {
    if (!data) return [];
    const needle = q.trim().toLowerCase();
    const filtered = data.filter((r) =>
      (tier === "All" || r.tier === tier) && (action === "All" || r.action === action) && matchesEvidence(r, evidence) &&
      (!needle || `${r.name} ${r.industry ?? ""} ${r.country ?? ""}`.toLowerCase().includes(needle)));
    return [...filtered].sort((a, b) =>
      sort === "name" ? a.name.localeCompare(b.name) : ((b[sort] ?? -1) as number) - ((a[sort] ?? -1) as number) || a.id - b.id);
  }, [data, q, tier, action, evidence, sort]);

  function update(key: string, value: string, empty = "All") {
    const next = new URLSearchParams(params);
    if (value && value !== empty) next.set(key, value); else next.delete(key);
    setParams(next, { replace: true });
    setSelected(null);
  }

  if (loading && !data) return <Loading />;
  if (error || !data) return <ErrorBox message={error ?? "No data returned."} onRetry={reload} />;
  const pursue = data.filter((r) => (r.action === "CONTACT" || r.action === "PRIORITIZE") && !["Won", "Lost"].includes(r.stage)).length;

  return (
    <div>
      <PageHeader eyebrow="Account intelligence" title="Prioritized accounts"
        description={<>Every account scored by deterministic rules: <b className="font-semibold text-ink">fit</b> (out of 80) plus <b className="font-semibold text-ink">intent</b> (out of 20). {pursue} open account{pursue === 1 ? "" : "s"} currently {pursue === 1 ? "warrants" : "warrant"} outreach.</>}>
        <Link to="/app/compare" className="btn-secondary">Compare accounts</Link>
        <div className="segmented" role="group" aria-label="View">
          <button type="button" aria-pressed={view === "table"} onClick={() => update("view", "table", "table")}>Table</button>
          <button type="button" aria-pressed={view === "map"} onClick={() => update("view", "map", "table")}>Fit × intent map</button>
        </div>
      </PageHeader>

      <div className="mb-3 grid gap-2 sm:grid-cols-2 lg:grid-cols-[minmax(200px,1fr)_repeat(3,minmax(0,170px))_auto]">
        <label className="relative">
          <span className="sr-only">Search accounts</span>
          <Search className="pointer-events-none absolute left-2.5 top-1/2 h-4 w-4 -translate-y-1/2 text-ink-4" aria-hidden />
          <input className="input pl-8" placeholder="Search name, industry, country" value={q} onChange={(e) => update("q", e.target.value, "")} />
        </label>
        <select className="input" aria-label="Tier" value={tier} onChange={(e) => update("tier", e.target.value)}>
          {TIERS.map((t) => <option key={t} value={t}>{t === "All" ? "All tiers" : t}</option>)}
        </select>
        <select className="input" aria-label="Recommended action" value={action} onChange={(e) => update("action", e.target.value)}>
          {ACTIONS.map((a) => <option key={a} value={a}>{a === "All" ? "All actions" : a}</option>)}
        </select>
        <select className="input" aria-label="Evidence" value={evidence} onChange={(e) => update("evidence", e.target.value, "all")}>
          {EVIDENCE.map((x) => <option key={x.key} value={x.key}>{x.label}</option>)}
        </select>
        <div className="flex items-center gap-2">
          <label htmlFor="sort" className="text-xs text-ink-3">Sort</label>
          <select id="sort" className="input py-2" value={sort} onChange={(e) => setSort(e.target.value as SortKey)}>
            <option value="total">Total</option><option value="fit">Fit</option><option value="intent">Intent</option><option value="name">Name</option>
          </select>
        </div>
      </div>
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2 text-xs text-ink-4">
        <span className="num">{rows.length} of {data.length} accounts</span>
        {(q || tier !== "All" || action !== "All" || evidence !== "all") && (
          <button className="font-medium text-accent-700 hover:underline" onClick={() => { setParams(view === "map" ? { view: "map" } : {}, { replace: true }); setSelected(null); }}>Clear filters</button>
        )}
      </div>

      {view === "map" ? (
        <div className="grid gap-4 lg:grid-cols-[1.5fr_0.5fr]">
          <Panel title="Fit × intent" action={<span className="text-2xs text-ink-4">Select a point to inspect</span>}>
            <FitIntentMap rows={rows} selected={selected?.key ?? null} onSelect={(key, rs) => setSelected({ key, rows: rs })} />
            <div className="mt-3 flex gap-2 rounded-md border border-line bg-subtle px-3 py-2.5 text-xs text-ink-3">
              <Info className="mt-0.5 h-3.5 w-3.5 shrink-0" aria-hidden />
              <p>
                <b className="font-semibold text-ink-2">Fit</b>: {FIT_MEANING} <b className="font-semibold text-ink-2">Intent</b>: {INTENT_MEANING} The
                two axes are not independent: disqualifiers (too small, wrong industry or geography) lower fit and also subtract from intent,
                which is why many low-fit accounts sit at zero intent. Points are not jittered; accounts with identical scores share a point.
              </p>
            </div>
          </Panel>
          <Panel title={selected ? `${selected.rows.length} account${selected.rows.length > 1 ? "s" : ""} at this point` : "Selection"} flush>
            {selected ? (
              <ul className="max-h-[480px] divide-y divide-line overflow-y-auto">
                {selected.rows.map((r) => (
                  <li key={r.id} className="px-4 py-3">
                    <Link to={`/app/accounts/${r.id}`} className="font-medium text-ink hover:text-accent-700 hover:underline">{r.name}</Link>
                    <div className="mt-1 flex flex-wrap gap-1">{r.tier && <TierBadge tier={r.tier} />}<ActionBadge action={r.action} /></div>
                    <div className="num mt-1 text-xs text-ink-3">Fit {r.fit?.toFixed(1)} · Intent {r.intent?.toFixed(1)} · Total {r.total?.toFixed(1)}</div>
                  </li>
                ))}
              </ul>
            ) : <p className="panel-pad text-ink-3">Click or tab to a point to list its accounts. The table view shows the same data with exact values.</p>}
          </Panel>
        </div>
      ) : rows.length === 0 ? (
        <EmptyState title="No accounts match these filters">Clear the filters or choose another tier, action or evidence type.</EmptyState>
      ) : (
        <>
          <div className="panel hidden max-h-[calc(100vh-17rem)] overflow-auto md:block">
            <table className="tbl">
              <thead>
                <tr>
                  <th>Account</th>
                  <th title={FIT_MEANING}>Fit</th>
                  <th title={INTENT_MEANING}>Intent</th>
                  <th className="r">Total</th>
                  <th>Tier</th>
                  <th>Next action</th>
                  <th>Evidence</th>
                  <th>Stage</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((r) => (
                  <tr key={r.id} className="cursor-pointer hover:bg-subtle" onClick={() => navigate(`/app/accounts/${r.id}`)}>
                    <td>
                      <div className="flex items-center gap-1.5">
                        <Link to={`/app/accounts/${r.id}`} className="font-medium text-ink hover:text-accent-700 hover:underline" onClick={(e) => e.stopPropagation()}>{r.name}</Link>
                        {r.uses_synthetic_demo_additions && <span className="badge border-line-strong bg-subtle font-medium text-ink-3" title="Evidence includes a labelled synthetic demo note">demo note</span>}
                      </div>
                      <div className="text-2xs text-ink-4">{[r.industry, r.employee_count != null ? `${r.employee_count} employees` : null, r.country].filter(Boolean).join(" · ")}</div>
                    </td>
                    <td><Meter value={r.fit} max={80} label="Fit" /></td>
                    <td><Meter value={r.intent} max={20} label="Intent" /></td>
                    <td className="r font-semibold">{r.total?.toFixed(1) ?? "—"}</td>
                    <td>{r.tier ? <TierBadge tier={r.tier} /> : <span className="text-ink-4">Unscored</span>}</td>
                    <td><ActionBadge action={r.action} /></td>
                    <td><EvidenceChips counts={r.evidence} /></td>
                    <td className="text-ink-3">{r.stage}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <ul className="panel divide-y divide-line md:hidden">
            {rows.map((r) => (
              <li key={r.id}>
                <Link to={`/app/accounts/${r.id}`} className="block px-4 py-3 hover:bg-subtle">
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <div className="truncate font-medium text-ink">{r.name}</div>
                      <div className="mt-1 flex flex-wrap gap-1">{r.tier && <TierBadge tier={r.tier} />}<ActionBadge action={r.action} /></div>
                    </div>
                    <div className="num text-right text-lg font-semibold">{r.total?.toFixed(1) ?? "—"}</div>
                  </div>
                  <div className="mt-2 grid grid-cols-2 gap-3"><Meter value={r.fit} max={80} label="Fit" /><Meter value={r.intent} max={20} label="Intent" /></div>
                  <div className="mt-2"><EvidenceChips counts={r.evidence} /></div>
                </Link>
              </li>
            ))}
          </ul>
        </>
      )}
    </div>
  );
}

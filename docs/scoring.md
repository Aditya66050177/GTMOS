# GTMOS Scoring Engine Specification

The GTMOS scoring engine evaluates target accounts against a product's structured Ideal Customer Profile (ICP) using an explainable, 100-point deterministic model.

## Score Breakdown (Total: 100 Points)

| Component | Max Points | Evaluation Rules |
|---|---|---|
| **ICP Fit** | 30 pts | • **Industry Exact Match**: 20 pts if account industry matches ICP target industries.<br>• **Adjacent Industry**: 10 pts if industry is adjacent (e.g. B2B SaaS, Software, Tech).<br>• **Pain Point Overlap**: Up to 10 pts for keyword matches in account description matching ICP pain points solved (5 pts per matched pain point). |
| **Company Fit** | 20 pts | • **Target Employee Range**: 20 pts if employee count is inside `[min_employees, max_employees]`.<br>• **Near Target Range**: 10 pts if within 25% outside the target range.<br>• **Exclusion Penalties**: -20 pts if account industry/description matches disqualifying exclusion criteria. |
| **Technology Fit** | 15 pts | • **Tech Stack Overlap**: Proportional points based on matching tech stack items between account and ICP requirements (capped at 15 pts). Default 10 pts if no tech requirements specified in ICP. |
| **Buying Intent** | 20 pts | **Signal Engine**: Evaluates buying signals (e.g., support_hiring, funding, product_launch, rapid_growth) extracted from raw research. Scores are weighted by signal type, multiplied by extraction confidence and strength, and decayed by recency (50% value after 90 days, 0% after 180 days). Deterministic negative signals (too_small, wrong_industry, wrong_geography, no_use_case) apply heavy penalties. Capped at 20 pts. |
| **Geography Fit** | 15 pts | • **Exact Country Match**: 15 pts if country is in target geographies.<br>• **Regional Match**: 8 pts if country is in same broader region.<br>• **No Match**: 0 pts. |

## Tier Classification

| Total Score | Priority Tier | Description |
|---|---|---|
| **90 – 100** | **Priority 1** | Immediate outreach target with strongest ICP alignment. |
| **75 – 89** | **Priority 2** | Strong fit candidate; recommended for standard GTM campaigns. |
| **50 – 74** | **Priority 3** | Moderate fit; nurture or monitor for future intent signals. |
| **< 50** | **Low** | Poor alignment or disqualified by exclusion criteria. |

## Reasoning & Provenance
Every account scoring run produces a structured JSON output containing:
1. Component breakdown table (`component`, `score`, `max_score`).
2. Detailed reason list (`rule`, `met`, `text`, `points`).
3. Total score and assigned priority tier.

---

## Worked Example: Acme Technologies

Acme Technologies is an enterprise SaaS platform with 250 employees in the United States, utilizing Zendesk and Salesforce, backed by Series B funding, with an 18-person customer support team.

### Account Profile
- **Industry**: `B2B SaaS`
- **Employee Count**: `250`
- **Country**: `US`
- **Tech Stack**: `["Zendesk", "Salesforce"]`
- **Funding**: `Series B`
- **Support Team Size**: `18`
- **Detected Signals**: `support_hiring` (strength: 0.9, confidence: 0.85, 30 days old)

### 100-Point Score Breakdown

| Component | Awarded / Max | Rule Applied & Explanation |
|---|---|---|
| **ICP Fit** | **30.0 / 30.0** | Exact match on industry `B2B SaaS` (20.0 pts) + matched pain point overlap on "support ticket volume" (10.0 pts). |
| **Company Fit** | **20.0 / 20.0** | Employee count (250) falls squarely within the target ICP employee range of `[50, 500]`. No disqualifying exclusions matched. |
| **Technology Fit** | **15.0 / 15.0** | Tech stack includes both `Zendesk` and `Salesforce`, matching core ICP tech requirements. |
| **Buying Intent** | **12.0 / 20.0** | `support_hiring` signal detected (base weight: 20 pts) decayed by recency (30 days old = factor ~0.83) multiplied by extraction confidence (0.85) = ~12.0 pts. |
| **Geography Fit** | **15.0 / 15.0** | Country `US` exactly matches target ICP geographies (`US`, `Canada`). |
| **Total Score** | **92.0 / 100.0** | **Tier: Priority 1** (Total >= 90.0) |

**Resulting Recommendation**: `CONTACT` — Priority 1 account with strong intent signals detected. Suggested angle: *support team scaling and efficiency*.

---

## Frequently Asked Questions (FAQ)

### 1. What happens if no ICP exists in the database?
If an account is scored before an ICP is generated for the product, `ScoringEngine.score_account()` raises a `ValueError("No ICP Profile for product ... Generate ICP first.")`. You can generate an ICP automatically via `ICPEngine.generate_icp_for_product()`.

### 2. Can I manually override the intent score?
Yes. The pure calculation method `ScoringEngine.compute_score()` accepts an `AccountData` object with an optional `intent_score_override: Optional[float]`. When provided, the scorer uses this value directly instead of computing proxy intent from support team size and funding stage.

### 3. What triggers exclusion criteria penalties?
If an account's industry or description contains keywords matching `icp.exclusions` (such as `"B2C Only"`, `"Government"`, `"Healthcare"`, or `"Hardware manufacturing"`), the Company Fit score receives an immediate penalty of `-20 points`, bringing Company Fit to `0.0`.

### 4. How does recency decay affect intent signals?
Signals maintain 100% value for the first 30 days. Beyond 30 days, linear decay reduces the signal weight down to 50% at 90 days, and 0% at 180 days. Stale signals (>180 days) do not contribute to buying intent.

### 5. Why are tie-breaking scores deterministic?
All component calculations rely solely on explicit arithmetic rules and set intersections. No random seeds, stochastic sampling, or LLM temperatures are involved in scoring. Repeated executions on identical account data always return the exact same score and tier.


# GTMOS — Go-To-Market Strategy (hypotheses)

**Status labels used throughout:**
- **[Assumption]**: reasoning, not tested.
- **[Synthetic finding]**: observed in GTMOS's synthetic demo data; says nothing about real buyers.
- **[Validated]**: confirmed with real users or data. **Nothing in this document is validated yet.**
  There have been no customer interviews, pilots or sales.

---

## 1. Initial ICP hypothesis (for GTMOS itself)

**[Assumption]** The first users are **founder-led or early-stage B2B SaaS sales teams**:

| Attribute | Hypothesis | Reasoning |
|---|---|---|
| Stage | Seed to Series A | Outbound is still run by founders or the first sellers, who do research themselves |
| Team | 1–5 people doing outbound | GTMOS supports one product, one ICP and low volume |
| Motion | Account-based outbound to mid-market B2B | Account research is the bottleneck, not contact volume |
| Product | Technical or B2B SaaS with a clear buyer | Signals like hiring, funding and launches map to need |
| Values | Control and explainability over automation | GTMOS's differentiator is traceable decisions and human approval |

**Disqualifiers [Assumption]:**
- high-volume SDR teams that need sequencing and contact data
- teams that require CRM sync on day one
- regulated industries needing a security review before any pilot
- companies with no outbound motion

**Segments considered and deprioritized for now [Assumption]:**
- **Outbound agencies:** strong pain, but they need multi-client workspaces, volume and
  enrichment, none of which GTMOS has.
- **Larger sales teams:** they need CRM integration and seats.
- **"Anyone selling B2B":** too broad to learn from.

## 2. Buyer personas [Assumption]

| Persona | Cares about | GTMOS angle |
|---|---|---|
| **Founder doing sales** | Using scarce hours on the right accounts; not embarrassing the brand | A short, explained list of who to contact and why, with drafts they approve |
| **First sales hire / AE** | Pipeline from limited accounts; credible personalization | Evidence quotes to open with; a check that drafts state only true facts |
| **Head of GTM / RevOps (later)** | Consistent qualification; why reps pick accounts | Auditable rules and fit/intent separation they can tune |

## 3. Problem intensity [Assumption]

The problem is felt weekly ("who do I contact this week?"), but it competes with every other
founder priority. Intensity is probably highest:
- right after a funding round, when there are outbound targets but no team yet
- when a new ICP or market is being tested
- when a bad AI-written email has already caused embarrassment

None of this has been measured.

## 4. Existing alternatives [Assumption]

| Alternative | What it does well | Where GTMOS differs |
|---|---|---|
| Spreadsheet + manual research | Free, flexible, fully controlled | GTMOS adds consistent rules, decay, and evidence capture with rejection |
| CRM lead/account scoring | Lives where reps work | Often opaque; GTMOS shows every point and rule |
| Data and enrichment platforms (e.g. Apollo, ZoomInfo, Clay) | Contact data, enrichment, volume | GTMOS has none of that; it's a qualification and explanation layer |
| Intent platforms (e.g. 6sense, Common Room) | Broad intent data | GTMOS is transparent but has no data network |
| ChatGPT-style assistants | Fast research and drafting | GTMOS refuses unverified claims and never lets the model decide |

I haven't researched competitor pricing or feature details; the descriptions above are
general characterisations.

## 5. Positioning [Assumption]

> **For** founder-led B2B sales teams **who** have more possible accounts than time,
> **GTMOS** is an account prioritization tool **that** separates fit from buying intent and
> shows the evidence behind every recommendation. **Unlike** opaque lead scores or chat
> assistants, **every point traces to a rule or a quoted source, and no message is sent
> without a person's approval.**

## 6. Value proposition [Assumption]

1. **Spend outreach on fewer, better-timed accounts.** In the synthetic demo, 3 of 150
   accounts are flagged for outreach, 5 for nurture [Synthetic finding].
2. **Trust the reasoning.** Each recommendation cites its rule; each signal its quote.
3. **Don't embarrass the brand.** Drafts use verified evidence; a person approves everything.

## 7. Account qualification

**Fit (out of 80):** ICP fit 30, company fit 20, technology fit 15, geography fit 15.
**Intent (out of 20):** verified signals, minus disqualifier penalties.
**Tiers:** Priority 1 ≥ 90, Priority 2 ≥ 75, Priority 3 ≥ 50, Low < 50.
**Actions:** see the rule table in `docs/PRODUCT_CASE_STUDY.md` §7.

Qualification questions a seller would ask beyond the score [Assumption]: Is there an owner
for the problem? Is the trigger recent and confirmed? Is the timing compatible with their
buying cycle?

## 8. Fit versus intent as a GTM motion

| | Low intent | High intent |
|---|---|---|
| **High fit** | **Research** for a trigger; don't cold-call yet (Company 37 Cloud: fit 80, intent 0 → RESEARCH) | **Contact now** (Fintech Pulse: fit 78.5, intent 15.2 → CONTACT) |
| **Moderate fit** | **Deprioritize** (Acme: fit 69.5, intent 0 → DEPRIORITIZE) | **Prioritize**: timing can outweigh imperfect fit (Company 36: fit 57, intent 20 → PRIORITIZE) |

These four cases are **[Synthetic findings]**; Company 36's signals come from labelled
synthetic notes. Whether the motion works on real accounts is untested.

## 9. Buying signals

| Signal | Weight | Why it might indicate need (product hypothesis, for a support-automation product) |
|---|---|---|
| Support hiring | 20 | Ticket volume growing faster than the team |
| Funding | 15 | Mandate and budget to scale tooling |
| Product launch | 15 | A wave of new customer questions |
| Relevant technology | 15 | Integrates with tools they run, so lower adoption cost |
| International expansion | 10 | New languages, time zones and support load |
| Rapid growth | 10 | Growth outpaces support capacity |
| Executive change | 5 | A new leader reviews tooling |

Signals decay (full weight up to 90 days, half up to 180, none after), and only verified
quotes count. Negated, hearsay and speculative claims are recorded with 0 points.

**[Synthetic finding]** Verified signals are sparse: 41 of 150 accounts have one, and only 2
have intent ≥ 15. In 23 accounts, disqualifier penalties cancel the signal points entirely.
Real data could look very different.

## 10. Outreach strategy [Assumption]

- Lead with the specific, verified trigger (quoted), not a generic pitch.
- Match persona to signal (e.g. funding → CRO, support hiring → VP of Customer Support), as
  the rule table already suggests.
- One short message (under 120 words), human-approved, sent by a person.
- Research before contacting high-fit, no-intent accounts.

## 11. Pilot strategy [Assumption]

| Element | Plan |
|---|---|
| Format | Free, supervised **design-partner pilot**, 4–6 weeks, 2–3 teams |
| Setup | The team's real product description and ICP; their target account list; real research notes |
| What GTMOS needs first | Real authentication and an isolated workspace, managed database, a data-handling statement, CSV import. **None of these exists yet** |
| What the team gives | Weekly 20-minute feedback; outcome data on accounts contacted (replied / meeting / no response) |
| What they get | A prioritized, explained list each week; drafts they can approve; a final readout |
| After | Decide together: continue, change, or stop. No paid offer until value is measured |

## 12. Activation and retention hypotheses [Assumption]

- **Activation:** the team approves its first evidence-backed draft and sends it, within the
  first session after importing accounts.
- **Aha moment:** seeing a high-fit account correctly told "research, not contact" because
  the only "signal" was a rumour.
- **Retention:** a weekly habit of reviewing the "worth pursuing" and "investigate next"
  lists. Retention depends on new research notes arriving, which needs a sustainable
  research input.

## 13. Metrics to validate product value

| Metric | Question it answers | How |
|---|---|---|
| Reply / meeting rate on GTMOS-recommended accounts vs the team's own picks | Does prioritization improve outcomes? | Pilot with a comparison group |
| Share of recommendations acted on | Do users trust it? | Track approve vs ignore |
| Draft edit rate and reasons | Are drafts usable and correct? | Compare `original_body` with the approved body |
| False-signal reports | Is evidence checking good enough? | A user flag on signals |
| Weekly active use | Is it a habit? | Sessions per team per week |
| Time to a prioritized list | Is it faster than the current workflow? | Timed onboarding |

**[Synthetic finding] only:** the demo pipeline's 42.7% Contacted → Replied conversion and 3
won deals come from a simulation and must not be quoted as performance.

## 14. Pricing (hypothesis only)

No willingness-to-pay data exists.
- **[Assumption]** A free design-partner pilot comes first.
- After that, possibly a small paid pilot or a per-seat subscription aimed at founder-led
  teams.

Price points should come from pilot conversations, not from this document.

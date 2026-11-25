# GTMOS — Five-minute executive demo script

Matches the six-step guided demo at `/demo`. The six steps total 5:00; allow about 20 seconds more for the opening and close. All data is synthetic and the
pipeline is simulated; say so once at the start and once at the end.

**Before you start:** open the landing page, then click **Explore the 5-minute demo** →
**Start the 5-minute demo**. On a laptop the guide docks on the right; use **Next** to move
between steps. If you reset the sandbox during the demo, the review queue starts fresh.

---

## Opening (10 seconds, on `/demo`)

**Say:** "Everything you'll see is synthetic: 150 made-up companies and a simulated
pipeline. What I want to show you is the decision logic, not the data."

---

## Step 1 — The business problem (0:30) · Overview `/app`

**Say:** "Picture yourself leading GTM with 150 possible accounts and one or two sellers.
GTMOS asks two separate questions. Fit: does this company look like our customer? Intent: is
there evidence of a reason to act now? Most tools blend those into one score; I think that
hides the most useful decision."

**Click:** nothing. Point at the KPI row and the tier distribution.

**Notice:** 31 of 150 accounts are Priority 1 or 2, but only a handful have any verified
buying signal.

**Business question:** *Where should limited sales capacity go?*

**Likely follow-ups:**
- *"Where do the 150 accounts come from?"* A synthetic CSV. In a real pilot it would be the
  team's own target list (CSV import isn't built yet).
- *"Is 31 high-priority accounts a lot?"* That's fit plus whatever intent exists. Step 3 shows
  why only 3 warrant outreach now.

## Step 2 — Define the ICP (0:45) · Methodology `/app/methodology#icp`

**Say:** "This starts from a product description; here, a support-automation product. A
language model proposes the ideal customer profile, but its output has to pass a strict
schema, and after that the model has no say in scoring. Fit is 80 points across four rules
you can read: industry and pain points, size, tech stack, geography. Intent is the other 20.
Same inputs, same score, every time."

**Click:** scroll from the ICP to the "100-point score" table.

**Notice:** the plain-language rule next to every component, and the weights.

**Business question:** *Who is our customer, and how do we judge resemblance consistently?*

**Likely follow-ups:**
- *"Why rules instead of machine learning?"* There's no outcome data to learn from yet, and
  rules are auditable. A sales leader can disagree with a specific rule and change it.
- *"Who chose the weights?"* I did, as reasoned defaults. They're untuned, and the methodology
  page lists that as a weakness.

## Step 3 — Prioritize accounts (1:15) · Fit × intent map `/app/accounts?view=map`

**Say:** "Here's every account by fit across and intent up. The dashed lines are the tier
boundaries; tiers come from fit plus intent. Look at three cases. Company 37 Cloud has
perfect fit, 80 out of 80, and zero intent: the recommendation is *research*, not call.
Company 36 fits less well, 57, but has two current, verified signals worth 20: it gets
*prioritize*. Fintech Pulse has both, so it's *contact*. Same tier doesn't mean same action:
within a tier, intent decides."

**Click:** the point at the top (Company 36), then the cluster at the far right on the
x-axis (Company 37's group). Optionally: **Compare these accounts side by side**.

**Notice:**
- Most points sit at zero intent: signals are rare in this data.
- Points aren't jittered; accounts with identical scores share one point.
- The note says fit and intent aren't independent.

**Business question:** *Who deserves attention this week, and why not just the best-fit accounts?*

**Likely follow-ups:**
- *"Isn't Company 36 cherry-picked?"* Yes. I added two labelled synthetic notes so the data
  would contain this contrast, and the scoring engine (unchanged) produced the result. It's
  flagged in the UI.
- *"Why are so many accounts at zero intent?"* Verified signals are sparse, and in 23 accounts
  disqualifier penalties cancel the signal points completely.

## Step 4 — Inspect evidence (1:15) · Company 36's evidence `/app/accounts/{id}#evidence`

**Say:** "This is what I care most about. Each signal shows the original sentence from the
research note, with the exact quote highlighted. It's never paraphrased. Then the arithmetic:
support hiring is weight 20 × strength 0.8 × confidence 0.9 × recency 1.0 = 14.4 points. The
funding note adds 12.15. Together they exceed 20, so intent caps at 20. And here's a claim it
refused: 'We are not hiring right now' is negated, recorded, and worth zero."

**Click:** scroll through the two signals and the rejected claim. Then click **Acme: rumour
rejected** in the guide.

**Notice:**
- Acme's "hiring" rumour, contradicted by a freeze, is rejected.
- The line at the bottom confirms the recomputed intent matches the stored score.

**Business question:** *Can I trust why this account is ranked here?*

**Likely follow-ups:**
- *"What if the AI hallucinates a signal?"* The quote must appear in the note, or the signal
  is rejected and logged.
- *"Who extracts signals in this demo?"* An offline, rule-based stand-in for the language
  model, so the public demo costs nothing and is reproducible. It has gaps: it still accepts
  "reportedly" claims.
- *"Do old signals count?"* Full weight up to 90 days, half up to 180, nothing after.

## Step 5 — Prepare outreach (0:45) · Review queue `/app/review`

**Say:** "Drafts only use verified evidence: each one names its signal and shows the quote.
A fact-check refuses any number that isn't in that evidence. And approving doesn't send
anything; GTMOS has no code path that sends email. A person sends it and logs it here. One
honest caveat: in this public demo your approvals live in a temporary sandbox and can reset,
and the app tells you if that happens."

**Click:** **Approve** on one draft, then open the **Approved** tab. It reads "approved — not
sent". Optionally: **Draft outreach for Company 36 B2B** in the guide.

**Notice:** the evidence panel beside each draft; the status wording never implies sending.

**Business question:** *How do we personalize at speed without risking the brand?*

**Likely follow-ups:**
- *"Why not auto-send?"* One wrong claim in a first email can cost the account. Review is the
  product's job, not a missing feature.
- *"Does the fact-check catch everything?"* No. It checks numbers, not every claim.

## Step 6 — Ask the analyst (0:30) · Executive questions `/app/analytics#executive`

**Say:** "Last, the questions a GTM leader actually asks. These answers are built by code from
database queries, with no generated SQL. Observations are read straight off the data;
hypotheses are labelled as unproven. And the pipeline is a simulation, so none of this says
anything about real buyers."

**Click:** **Which accounts are worth pursuing?** (3 accounts). If time allows, **Where are
opportunities getting stuck?** It shows the Contacted → Replied drop and that 33 of 42 stalled
accounts are Priority 3 or Low.

**Notice:** the two columns, Observations vs Hypotheses, and the "demo note" tag on Company 36.

**Business question:** *What should the team do next, and how sure are we?*

**Likely follow-ups:**
- *"Can it answer any question?"* No. It maps questions to 11 fixed queries; anything else
  returns "unknown". That's deliberate.
- *"Are those conversion rates real?"* No. They're simulated.

---

## Close (10 seconds)

**Say:** "To be clear about limits: on a labelled test set, tier accuracy is 57%, and it never
gets Priority 2 right. The methodology page explains why. My next step isn't more features;
it's testing this with two or three real sales teams."

## If the demo misbehaves

- **"Your earlier demo changes are no longer shown":** the sandbox expired or another server
  answered. Say "that's the demo being honest about temporary data" and continue.
- **Slow first load (about 4 seconds):** the demo database is rebuilt on a cold start.
- **An account link doesn't resolve:** the guide falls back to the account list and says so.

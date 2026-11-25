# GTMOS — Presentation outline (7–10 minutes, 10 slides)

Business first: problem → judgment → product → evidence → limits → learning. Keep a laptop
ready with `/demo` open; slide 6 is a live walkthrough, not screenshots.

**Timing guide:** slides 1–5 ≈ 3.5 min · slide 6 (demo) ≈ 3 min · slides 7–10 ≈ 3 min.

---

### Slide 1 — The business problem
**On the slide:** "150 accounts. One seller. Which ones this week?"

**Speaker notes:** Every outbound team has more possible accounts than time. The real
question isn't "who could buy?" but "who should we spend this week's hours on, and why now?"
I built GTMOS to explore how a tool can answer that in a way a sales leader would trust.

### Slide 2 — Why prioritization is hard
**On the slide:** three bullets: fit ≠ timing · scores nobody can explain · AI that states
things that aren't true

**Speaker notes:** Three failure modes. First, lists sorted by firmographic fit ignore
timing, so good-fit accounts get called with no reason to listen. Second, lead scores are
often black boxes, so reps don't trust or challenge them. Third, AI assistants write fluent
research but can state things that aren't in the source, which is risky in a first email.
These are my reasoning about common workflows; I haven't run interviews yet.

### Slide 3 — GTMOS in one sentence
**On the slide:** "Fit and intent, scored separately, every point traceable, and a person
approves every message."

**Speaker notes:** GTMOS turns a product description into an ideal customer profile, scores
150 synthetic accounts, finds buying signals in research notes, recommends a next action,
and drafts outreach for a person to approve. The design rule: AI handles language;
deterministic, tested code makes the business decisions. The model never scores or decides.

### Slide 4 — Fit versus intent
**On the slide:** a 2×2 grid with the four demo accounts:
- **Company 37:** fit 80, intent 0 → **RESEARCH**
- **Company 36:** fit 57, intent 20 → **PRIORITIZE**
- **Fintech Pulse:** 78.5 / 15.2 → **CONTACT**
- **Acme:** 69.5 / 0 → **DEPRIORITIZE**

**Speaker notes:** Fit asks "do they look like our customer?" (out of 80). Intent asks "is
there credible evidence of a reason to act now?" (out of 20). Company 37 has perfect fit and
is told to research. Company 36 fits worse and is told to prioritize, because it has two
current, verified signals. Same tier, different action: within a tier, intent decides. Be
upfront that Company 36's signals come from labelled synthetic notes I added to show this
contrast, and that the two scores aren't fully independent, because disqualifiers lower both.

### Slide 5 — Evidence-backed prioritization
**On the slide:** one signal shown as source sentence (quote highlighted) →
`20 × 0.8 × 0.9 × 1.0 = 14.4 pts`, next to a rejected claim: "hiring freeze → negated, 0 pts"

**Speaker notes:** A signal only counts if its quote is actually in the research note. Each
one shows weight, strength, confidence and recency decay, so you can do the arithmetic
yourself. Claims the system refuses (negated, rumoured, speculative) are kept and shown with
zero points, not hidden. That's how Acme's "hiring" rumour, contradicted by a hiring freeze,
doesn't put it on the call list.

### Slide 6 — Live walkthrough (≈ 3 min)
**On the slide:** "Live demo: gtmos /demo". Follow `docs/EXECUTIVE_DEMO_SCRIPT.md`,
compressed to steps 3, 4 and 6.

**Speaker notes:**
- **Map:** show Company 37 vs Company 36.
- **Account page:** show the highlighted quote, the formula and the rejected claim.
- **Analytics:** click "Which accounts are worth pursuing?" and point out observations vs
  labelled hypotheses.

If short on time, skip the review queue but say one sentence: approving never sends; a
person sends.

### Slide 7 — Architecture and product decisions
**On the slide:** a simple stack diagram (React → FastAPI → engines → SQLite; LLM adapter on
the side) and four decision bullets.

**Speaker notes:** The decisions matter more than the stack:
- deterministic scoring, because it's auditable and there's no outcome data to train on
- quote-verified signals, with rejections stored
- an analyst that can only choose from fixed queries (no generated SQL)
- a public demo where visitors' edits live in private, temporary sandboxes, which tell
  you when your edits are lost

### Slide 8 — Evaluation and limitations
**On the slide:** **57% tier accuracy** · **0% Priority 2 recall** · confusion-matrix thumbnail.
Caveats: synthetic data · simulated pipeline · no customers

**Speaker notes:**
- **The weak spot:** on 100 labelled synthetic accounts the model gets 57% of tiers right
  and never identifies a true Priority 2. All 19 are predicted Priority 1.
- **I traced why:** those accounts have no research notes, so the evaluation uses a built-in
  proxy for intent (support-team size and funding stage) that pushes good-fit accounts over 90.
- **The 100% signal score** comes from a simplified matcher on easy sentences, so I don't
  lean on it.
- **The data:** everything is synthetic, and the pipeline is simulated. There are no
  customers or revenue numbers.

I'd rather show this than an impressive unexplained number.

### Slide 9 — What I learned
**On the slide:** four short lines:
- "Why now" matters more than "who fits".
- Explainability is a feature.
- Data bugs look like insights.
- Honest metrics build trust.

**Speaker notes:** Use your own words; see the guidance in `docs/GTMO_INTERVIEW_PREPARATION.md`
§B. The strongest concrete example is that an early version showed 37 Priority 1 accounts.
That turned out to be bugs: signals loaded twice, "not hiring" counted as hiring, and notes
pointing at accounts that didn't exist. Fixing them cut Priority 1 to 2. The tool had looked
more useful than it was.

### Slide 10 — What I'd build next
**On the slide:** 1) talk to 10 sales teams · 2) 2–3 supervised pilots · 3) recalibrate
scoring on real outcomes · 4) evaluate a live model on real notes

**Speaker notes:** The next step isn't more features. It's evidence. Before building CRM sync
or multi-tenant infrastructure, I'd want to learn whether recommended accounts actually reply
or book meetings more often than a team's own picks. Close with an invitation: "If your team
does outbound, I'd value 20 minutes on how you decide who to contact."

---

**One-line answers to have ready:**
- **Is it live?** It's built for Vercel but not deployed yet; I can run it locally.
- **Any users?** No. It's a prototype on synthetic data, and the next step is pilots.
- **Why not just ChatGPT?** It can write the email; it can't be trusted to decide or to
  state only verified facts, and GTMOS separates those jobs.

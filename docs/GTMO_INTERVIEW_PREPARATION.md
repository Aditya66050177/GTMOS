# GTMOS — Interview preparation

Answers are grounded in the implementation and its reports. Where something hasn't been
done (interviews, pilots, pricing research), the answer says so. Practise saying these in
your own words; don't recite them.

---

## Part A — 30 questions a GTM Head or Product leader might ask

### ICP selection

**1. Why this ICP (B2B SaaS, 50–500 employees, US)?**
It's the demo product's ICP, a synthetic support-automation tool, generated from its product
description and checked against a schema. It isn't a market claim. What I'd defend is the
*structure*: industries, size, geography, roles, pain points, tech and exclusions, each mapped
to a scoring rule.

**2. Who is GTMOS itself for, and how do you know?**
My hypothesis is founder-led or early sales teams at seed to Series A B2B companies, because
GTMOS handles one product, low volume, and values control. *I don't know yet;* I haven't run
customer interviews. That's the first thing I'd do.

**3. Why not target outbound agencies? They feel this pain most.**
They probably do, but they need multi-client workspaces, volume, enrichment and sending, which
GTMOS doesn't have. Starting there would mean building infrastructure before learning whether
the core idea works.

### Fit versus intent

**4. Why separate fit and intent instead of one score?**
Because they drive different actions. Company 37 (fit 80, intent 0) and Company 36 (fit 57,
intent 20) are both Priority 2; one should be researched, the other prioritized. One number
hides that.

**5. Are fit and intent really independent?**
No, and that's a design weakness I'd revisit. Disqualifiers (too small, wrong industry or
geography) lower fit *and* subtract from intent, so bad-fit accounts are penalised twice. It
also produces many zero-intent accounts.

**6. Isn't your best example (Company 36) staged?**
Yes. I added two clearly labelled synthetic notes so the dataset contained a moderate-fit,
strong-intent account. The baseline data and evaluation are untouched, and the unchanged
engine produced the result. The UI tags it as synthetic.

### Scoring reliability

**7. 57% tier accuracy. Why should I trust this?**
You shouldn't trust it as a predictor yet. 57% is measured on 100 author-labelled synthetic
accounts. What you *can* trust is that every score is reproducible and explained. The
accuracy problem is concentrated and diagnosable (next question), which is more useful than
a vague 80%.

**8. Explain the 0% Priority 2 recall.**
All 19 true Priority 2 accounts are predicted Priority 1. The labelled accounts have no
research notes, so the evaluation uses the engine's built-in proxy for intent (support-team
size and funding stage, up to 20 points). For good-fit companies that pushes the total past
90. In the product, intent comes from verified signals instead, so the evaluation doesn't
even measure the product's real intent path. Both problems need fixing: a better proxy or
labelled notes, and threshold recalibration.

**9. Who chose the weights and thresholds? Are they tuned?**
I chose them as reasoned defaults. They aren't tuned against outcomes, because there are no
outcomes. With pilot data I'd start by checking whether reply rates differ by tier and by
signal type.

**10. What's the false-positive / false-negative trade-off you prefer?**
For outbound I'd rather miss some accounts than waste credibility on bad ones. The current
model is the opposite at the top: Priority 1 precision is 36.7% with 100% recall, so it
over-promotes. That's the first calibration target.

### Buying signal quality

**11. How do you stop the AI from inventing a signal?**
Code checks that the quoted evidence appears in the research note; if not, the signal is
rejected and logged as "unsupported" with 0 points. The model proposes; code verifies. Be
honest that the check is partial: for longer quotes it accepts a match on the first or last
three words, so a live model could slip a partly paraphrased claim through. Making it
whole-quote is a cheap fix I'd do before a pilot.

**12. Your signal precision is 100%. Isn't that suspicious?**
Yes, and I say so. It's measured with a simplified keyword matcher on 60 short synthetic
sentences, not the production extractor. It mostly shows the test is easy.

**13. What signals does it miss or get wrong?**
The offline extractor rejects negations ("not hiring", "hiring freeze") and rumours, but a
sentence like "the company reportedly raised a round" still counts. It doesn't understand
context beyond sentence-level rules. A live model would need its own evaluation on real notes.

**14. How do you handle old news?**
Decay: full weight up to 90 days, half up to 180, zero after. Only the newest signal of each
type counts. I found a bug where a note exactly 181 days old counted as 180 or 181 depending
on the time of day; it's fixed and pinned by a test.

### Deterministic rules vs LLM decisions

**15. Why not let the LLM score accounts? It's more flexible.**
Flexibility is the problem: the same account could score differently on two runs, and nobody
could explain why. Scores need to be auditable, repeatable and arguable. The model does what
it's good at: reading notes and writing drafts.

**16. Where exactly does the LLM run?**
- Proposing the ICP.
- Proposing signals from notes, which code then verifies.
- Writing drafts, which a fact-check and a person then review.
- Picking one of 11 fixed analytics queries.

It never scores, filters, computes or picks an action. In the public demo it runs as an
offline stand-in.

### Alternatives

**17. Why wouldn't a team just use ChatGPT?**
For writing, they might. GTMOS's difference is the decision layer: consistent rules across
150 accounts, a quote check that refuses invented claims, visible rejections, and a human
gate. ChatGPT can't tell you why account 37 ranks above account 36 the same way twice.

**18. Why not a spreadsheet?**
A spreadsheet can hold the same fields. What it doesn't do is quote-verify signals, decay
them, record rejected claims, or explain a recommendation rule by rule. A good RevOps person
could build some of it; the question is whether they'd maintain it.

**19. How is this different from Clay, Apollo or 6sense?**
Those bring data: contacts, enrichment, intent networks. GTMOS brings none; it's a
transparent qualification and explanation layer. It could sit on top of their data. I
haven't done a detailed competitive analysis.

### Measuring value, adoption, PMF and pricing

**20. How would you measure whether it improves sales productivity?**
In a pilot, compare reply and meeting rates on GTMOS-recommended accounts against the team's
own picks over the same weeks. Also track how often recommendations are acted on, and how
much reps edit drafts.

**21. What would make a team adopt it, and keep using it?**
- **Activation:** approving and sending a first evidence-backed draft.
- **Retention:** a weekly habit of reviewing "worth pursuing" and "investigate next".

Retention depends on fresh research notes arriving, which needs a sustainable input. That's
a real gap.

**22. Do you have product-market fit?**
No. There are no users, pilots or interviews. What I have is a testable hypothesis and a
prototype good enough to test it with.

**23. What would you charge?**
I don't have willingness-to-pay data, so I won't invent a number. I'd run a free supervised
design-partner pilot first, then test a small paid pilot or per-seat price based on what the
pilots show.

**24. What evidence would make you stop?**
If pilot teams' reply rates on recommended accounts weren't better than their own picks, or
if reps routinely ignored the recommendations, or if verified signals were too sparse on real
accounts to matter.

### Technical trade-offs, security and data

**25. Why SQLite and serverless? Will it scale?**
For a disposable synthetic demo it's the simplest option that works: zero setup, rebuilt on
each cold start. It won't hold customer data; pilots need managed Postgres (the code is
database-agnostic) and real authentication.

**26. Visitors can edit the public demo. Can they break it for others?**
No:
- Shared data is opened read-only.
- Only eight routes accept non-GET requests; everything else returns 403.
- Visitors' edits go to private, per-browser temporary sandboxes.
- There are rate limits and size caps.
- An adversarial review found no blocking issue for a synthetic-data demo.

**27. What happens when a visitor's edits disappear?**
Sandboxes live about two hours on one server instance. Each has a random token; if the
browser's remembered token is gone or different, the app shows "Your earlier demo changes
are no longer shown", and says they were never permanent and nothing was sent.

**28. Is any real or personal data involved?**
No. Companies, contacts (with `.example` emails) and notes are synthetic. The demo collects no
personal data. The browser ID is random and isn't authentication.

### Roadmap and judgment

**29. If you had three months, what would you build?**
Mostly I'd *learn*. In order:
1. 10 discovery conversations, then 2–3 supervised pilots on teams' real accounts.
2. Recalibrate scoring on those outcomes, starting with the Priority 2 problem and the double
   penalty.
3. Evaluate a live model on real notes.
4. Only then add auth, workspaces, CSV import and CRM sync.

**30. What would you change if you started again?**
I'd build the evaluation against the *product's* intent path from day one; the proxy hid the
real behaviour. And I'd write determinism and data-integrity tests earlier: duplicate signals
and notes pointing at missing accounts inflated results before anyone noticed.

---

## Part B — Talking about yourself (guidance, not a script)

### Describe your role accurately

From the repository history:
- **Your original build** (2026-10-14, two commits authored by you):
  - the FastAPI backend and the deterministic 100-point scoring engine
  - ICP generation, signal extraction with recency decay, the recommendation rule table
  - draft personalization with a guardrail, the CRM pipeline, analytics and the AI analyst
  - the Streamlit dashboard, the evaluation suite, n8n exports and the tests
- **The later work** (2026-11-25, twelve commits), implemented **with an AI coding assistant
  (Claude Code) under your direction**: bug fixes, the React web app, the public-demo
  security, the explainability and executive-analytics APIs, the redesign, the guided demo,
  and these documents.

  You set the objectives and constraints for each phase, reviewed each one, and approved or
  redirected it.

A fair way to say it:
> "I built the original engine. I then used an AI coding assistant to extend it into a
> public demo, while I set the direction, the constraints and the product decisions, and
> reviewed each phase."

Don't claim to have hand-written code you didn't. Interviewers increasingly value knowing
how to direct and check AI-assisted work, so be specific about what you decided and checked.

### Decisions that were yours (from the project history)

- **Honesty about weak results:** keeping the 57% accuracy and 0% Priority 2 recall visible
  everywhere instead of tuning them away.
- **The core rule:** "AI handles language; code decides", and no LLM-generated SQL.
- **Product framing:** separating fit from intent and making that the centre of the product.
- **The synthetic comparison:** approving a few clearly labelled notes, kept separate from the
  baseline and evaluation data, rather than editing the baseline.
- **Public-demo boundaries:** synthetic data only, offline AI, no auto-send, no fake customers
  or metrics, read-only shared data.
- **The sandbox fix:** asking that silently lost visitor edits be detected and explained
  honestly.
- **Phase discipline:** auditing before building, and stopping for review after each phase.

### Mistakes worth owning

These were bugs in the original version, found when the project was audited:
- Each signal was loaded twice, and "We are not hiring right now" counted as a hiring signal.
  Together they inflated Priority 1 from 2 to 37 accounts.
- 52 of 66 research notes named companies that didn't exist, so they were silently skipped.
- The draft fact-check logged failures but saved the draft anyway.
- Tests used the real database, so results depended on what had run before.
- The README's headline example (Acme ≈ 87, Priority 2) didn't match the data.

**The lesson:** I trusted outputs that looked plausible. Now I'd add data-integrity and
golden-file tests first.

### Things to say only if they're true for you

The repository can't tell anyone these, so answer from your own experience, or say you don't
have it yet:
- Why you chose this problem.
- Any conversations with salespeople or founders.
- What you personally found hardest.

### What feedback from a real GTM team would change the roadmap

- **"We don't have research notes for most accounts."** Make signal sourcing (or import)
  the priority over scoring refinements.
- **"We'd never act on a score we can't edit."** Build editable rules before anything else.
- **"Our best deals came from low-fit accounts."** Revisit fit weights and the double
  penalty.
- **"We need this inside our CRM."** Integration moves ahead of the standalone UI.

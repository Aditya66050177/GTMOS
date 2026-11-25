import type { PrioritizationRow } from "../lib/api";
import type { DemoKey } from "./DemoContext";

type Accounts = Partial<Record<DemoKey, PrioritizationRow>>;
export interface Link { label: string; to: string }
export interface Step {
  title: string;
  summary: string;
  duration: string;
  seconds: number;
  screen: string;
  target: (a: Accounts) => string;
  notice: (a: Accounts) => string[];
  more?: (a: Accounts) => Link[];
  needs?: DemoKey[];
}

const fmt = (r?: PrioritizationRow) =>
  r ? `fit ${r.fit?.toFixed(1)}/80, intent ${r.intent?.toFixed(1)}/20 → ${r.action}` : "not in the current dataset";
const acct = (r: PrioritizationRow | undefined, hash = "") => (r ? `/app/accounts/${r.id}${hash}` : "/app/accounts");

export const STEPS: Step[] = [
  {
    title: "The business problem",
    summary: "150 accounts, limited capacity: why fit alone is not enough to decide who to call.",
    duration: "0:30", seconds: 30, screen: "Overview",
    target: () => "/app",
    notice: () => [
      "You have 150 potential accounts and limited sales capacity. Which ones deserve your team's attention this week?",
      "GTMOS separates two questions. Fit: does this company look like our ideal customer? Intent: is there credible evidence of a reason to act now?",
      "Look at the tier distribution: most accounts are a poor fit, and only a handful combine fit with intent.",
    ],
  },
  {
    title: "Define the ICP",
    summary: "How a product description becomes a structured ICP and a deterministic 100-point model.",
    duration: "0:45", seconds: 45, screen: "Methodology: ICP and scoring",
    target: () => "/app/methodology#icp",
    notice: () => [
      "The product description becomes a structured ideal customer profile, validated against a schema before any rule uses it.",
      "Fit is worth 80 points (ICP 30, company 20, technology 15, geography 15). Intent is worth 20.",
      "Scoring is plain code: the same inputs always give the same score, and every point traces to a named rule.",
    ],
  },
  {
    title: "Prioritize accounts",
    summary: "The fit × intent map: high fit with no intent, moderate fit with strong intent, and why their actions differ.",
    duration: "1:15", seconds: 75, screen: "Fit × intent map",
    needs: ["c36", "c37", "fintech"],
    target: () => "/app/accounts?view=map",
    notice: (a) => [
      `High fit, no intent: ${a.c37?.name ?? "Company 37 Cloud"}, ${fmt(a.c37)}. A good-looking account with no reason to call yet.`,
      `Moderate fit, strong intent: ${a.c36?.name ?? "Company 36 B2B"}, ${fmt(a.c36)}. Two current, verified signals move it up.`,
      `Strong fit with credible signals: ${a.fintech?.name ?? "Fintech Pulse Inc"}, ${fmt(a.fintech)}.`,
      "Same tier does not mean same action: within a tier, intent decides. Dashed lines are the tier boundaries (fit + intent).",
    ],
    more: (a) => [
      { label: "Compare these accounts side by side", to: a.c36 && a.c37 && a.acme ? `/app/compare?ids=${a.c36.id},${a.c37.id},${a.acme.id}` : "/app/compare" },
    ],
  },
  {
    title: "Inspect evidence",
    summary: "Original sentences, highlighted quotes, decay and point contributions, and the claims GTMOS refuses to count.",
    duration: "1:15", seconds: 75, screen: `Account evidence`,
    needs: ["c36", "acme"],
    target: (a) => acct(a.c36, "#evidence"),
    notice: (a) => [
      `${a.c36?.name ?? "Company 36 B2B"}: each signal shows the original research sentence with the exact quote highlighted, its type, source and date.`,
      "Points = weight × strength × confidence × recency decay. Only the newest signal of each type counts.",
      "Rejected claims sit separately at 0 points. Here, \"We are not hiring right now\" is negated. On Acme, a hiring rumour contradicted by a freeze is rejected too.",
      "Note: Company 36's two buying signals come from labelled synthetic demo notes.",
    ],
    more: (a) => [
      { label: "Acme: rumour rejected", to: acct(a.acme, "#evidence") },
      { label: "Company 37: unsupported rumour", to: acct(a.c37, "#evidence") },
    ],
  },
  {
    title: "Prepare outreach",
    summary: "Drafts tied to verified evidence, and why a person must approve and send every message.",
    duration: "0:45", seconds: 45, screen: "Review queue",
    target: () => "/app/review",
    notice: () => [
      "Each draft names the buying signal it uses and shows the quoted evidence. A fact-check refuses any number not found in that evidence.",
      "Approving does not send anything. GTMOS never sends email: a person sends the message, then logs it here.",
      "Your approvals live in a temporary sandbox for this browser, kept about two hours on one server. They can reset if a different server handles your next visit.",
    ],
    more: (a) => [{ label: `Draft outreach for ${a.c36?.name ?? "Company 36 B2B"}`, to: acct(a.c36, "#outreach") }],
  },
  {
    title: "Ask the analyst",
    summary: "Executive questions answered from the database, with observations kept apart from labelled hypotheses.",
    duration: "0:30", seconds: 30, screen: "Executive questions",
    target: () => "/app/analytics#executive",
    notice: () => [
      "Pick a question. Answers are built by code from database queries: no generated SQL, no invented numbers.",
      "Observations are read off the data. Hypotheses are labelled as unproven interpretations.",
      "The pipeline is a 40-day simulation on synthetic accounts, so it says nothing about real buyers or revenue.",
    ],
    more: () => [{ label: "Methodology, evaluation and known weaknesses", to: "/app/methodology#evaluation" }],
  },
];

export const TOTAL = STEPS.reduce((s, x) => s + x.seconds, 0);

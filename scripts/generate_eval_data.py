"""
scripts/generate_eval_data.py
Generates data/eval/eval_accounts.csv and data/eval/eval_signals.csv
deterministically (seed=42). Run once to create the labeled evaluation dataset.
"""
import csv
import random
import sys
import io
from pathlib import Path
from datetime import date, timedelta

if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

random.seed(42)

OUT_DIR = Path(__file__).parent.parent / "data" / "eval"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
TODAY = date(2026, 10, 10)

def days_ago(n):
    return str(TODAY - timedelta(days=n))

# ---------------------------------------------------------------------------
# eval_accounts.csv — 100 labeled accounts
# Distribution: 30 high-fit (Priority 1 / 2), 35 medium (Priority 3), 35 low (Low)
# ---------------------------------------------------------------------------

ACCOUNTS = []

# ── HIGH FIT (30): B2B SaaS/Software, 50–500 employees, US/Canada, Zendesk/Intercom, Series B/C
HIGH_NAMES = [
    "Apex Support Solutions", "ClearDesk AI", "SupportScale Inc", "Helix CX Platform",
    "PulseDesk Technologies", "Orbit Customer Success", "Nimbus Help Platform",
    "Relay Support Ops", "Beacon CX Systems", "Clarity Desk AI",
    "Summit SaaS Corp", "Vortex Support Tech", "Echo Customer Platform",
    "Zenith Help Desk", "Atlas CX Solutions", "Nova Support Systems",
    "Crest B2B Software", "Spark Desk Technologies", "Wave CX Inc",
    "Ridge Support Solutions", "Core Help Platform", "Peak SaaS Inc",
    "Flux Customer Operations", "Prism B2B Systems", "Tide Support Tech",
    "Arch CX Platform", "Blaze Help Desk", "Drift Support Inc",
    "Glow SaaS Solutions", "Halo Customer Success",
]
HIGH_INDUSTRIES = ["B2B SaaS", "Software", "Cloud Services"]
HIGH_TECHS = [["Zendesk", "Salesforce"], ["Intercom", "Salesforce"], ["Zendesk", "Jira"],
              ["Freshdesk", "Salesforce"], ["Intercom", "Jira"], ["Zendesk", "Intercom"]]
HIGH_FUNDINGS = ["Series B", "Series C", "Growth"]
HIGH_COUNTRIES = ["US", "Canada", "United States"]
HIGH_EMPLOYEES = list(range(80, 480, 15))
HIGH_SUPPORT = list(range(15, 45))

for i, name in enumerate(HIGH_NAMES):
    emp = random.choice(HIGH_EMPLOYEES)
    techs = random.choice(HIGH_TECHS)
    tier = "Priority 1" if emp >= 200 and random.random() > 0.5 else "Priority 2"
    ACCOUNTS.append({
        "account_id": i + 1,
        "name": name,
        "industry": random.choice(HIGH_INDUSTRIES),
        "country": random.choice(HIGH_COUNTRIES),
        "employee_count": emp,
        "description": f"{name} is a B2B platform that automates customer support workflows and reduces ticket resolution time.",
        "technology_stack": "|".join(techs),
        "support_team_size": random.choice(HIGH_SUPPORT),
        "funding": random.choice(HIGH_FUNDINGS),
        "expected_tier": tier,
    })

# ── MEDIUM FIT (35): Adjacent industries, mixed size, mid funding
MED_NAMES = [
    "Crestwood E-Commerce", "Valley Cloud Services", "Horizon SaaS Group",
    "Meridian Tech Solutions", "Pinnacle Software Co", "Starlight Cloud Inc",
    "Westbrook Digital", "Fairview CRM Tech", "Lakeside Platform Corp",
    "Maple Grove Software", "Ironwood Cloud Group", "Cedarbrook SaaS",
    "Thornfield Tech", "Ashwood Digital Co", "Brookside Cloud",
    "Elmwood Software Inc", "Fireside B2B Group", "Greenhill Platform",
    "Hayfield Digital Tech", "Ivy League Software", "Juniper Cloud Corp",
    "Kingsley SaaS Systems", "Larkspur Digital Inc", "Maplewood Cloud",
    "Northbrook Software", "Oakdale Tech Group", "Parkside Digital",
    "Queensbury Cloud", "Riverside Software", "Silverwood Tech",
    "Timberline Digital", "Upland Cloud Inc", "Valleyview Software",
    "Windermere Tech", "Yellowstone Digital",
]
MED_INDUSTRIES = ["E-commerce", "Cloud Services", "Software", "Fintech", "EdTech"]
MED_TECHS = [["Salesforce"], ["Jira"], ["Intercom"], ["Freshdesk"], ["Zendesk"], []]
MED_FUNDINGS = ["Series A", "Seed", "Series B", "Bootstrap"]
MED_COUNTRIES = ["US", "United Kingdom", "Canada", "Australia", "Germany"]
MED_EMPLOYEES = list(range(200, 1000, 25))
MED_SUPPORT = list(range(5, 20))

for i, name in enumerate(MED_NAMES):
    emp = random.choice(MED_EMPLOYEES)
    techs = random.choice(MED_TECHS)
    ACCOUNTS.append({
        "account_id": len(ACCOUNTS) + 1,
        "name": name,
        "industry": random.choice(MED_INDUSTRIES),
        "country": random.choice(MED_COUNTRIES),
        "employee_count": emp,
        "description": f"{name} provides digital services and cloud-based tooling for mid-market clients.",
        "technology_stack": "|".join(techs),
        "support_team_size": random.choice(MED_SUPPORT),
        "funding": random.choice(MED_FUNDINGS),
        "expected_tier": "Priority 3",
    })

# ── LOW FIT (35): Wrong industry / size / country / no relevant tech
LOW_NAMES = [
    "GovTech Solutions LLC", "MediCare Systems Inc", "Hardware Direct Corp",
    "Steel Mills United", "Pharma Research Group", "National Infrastructure Co",
    "Defense Systems Ltd", "Agriculture Tech Corp", "Mining Operations Group",
    "Oil Field Services Inc", "Retail Giant Corp", "Auto Parts Supplier",
    "Food Processing Inc", "Logistics Heavy Freight", "Construction Materials Co",
    "Nuclear Energy Systems", "Water Treatment Corp", "Textile Manufacturing",
    "Print Media House", "Newspaper Corp Inc", "Television Broadcast Co",
    "Radio Networks Ltd", "Real Estate Holdings", "Property Management Co",
    "Insurance Agency Group", "Legal Services Corp", "Accounting Firm LLC",
    "Dental Practice Group", "Hospital Systems Inc", "Educational Institute",
    "K12 School District", "Government Agency", "Municipality Services",
    "Non-Profit Foundation", "Religious Organization",
]
LOW_INDUSTRIES = ["Healthcare", "Government", "Hardware Manufacturing", "Agriculture",
                  "Mining", "Oil & Gas", "Retail", "Legal Services", "Real Estate",
                  "Defense", "Media", "Non-Profit"]
LOW_COUNTRIES = ["Russia", "China", "North Korea", "Iran", "Brazil", "India", "Mexico"]
LOW_EMPLOYEES_SMALL = list(range(1, 30))
LOW_EMPLOYEES_BIG = list(range(2000, 10000, 200))

for i, name in enumerate(LOW_NAMES):
    # Mix of too small, too big, wrong industry, wrong country
    choice = i % 4
    if choice == 0:
        emp = random.choice(LOW_EMPLOYEES_SMALL)
        country = random.choice(HIGH_COUNTRIES)
        industry = random.choice(LOW_INDUSTRIES)
    elif choice == 1:
        emp = random.choice(LOW_EMPLOYEES_BIG)
        country = random.choice(HIGH_COUNTRIES)
        industry = random.choice(LOW_INDUSTRIES)
    elif choice == 2:
        emp = random.choice(range(50, 500))
        country = random.choice(LOW_COUNTRIES)
        industry = random.choice(LOW_INDUSTRIES)
    else:
        emp = random.choice(LOW_EMPLOYEES_SMALL)
        country = random.choice(LOW_COUNTRIES)
        industry = random.choice(LOW_INDUSTRIES)

    ACCOUNTS.append({
        "account_id": len(ACCOUNTS) + 1,
        "name": name,
        "industry": industry,
        "country": country,
        "employee_count": emp,
        "description": f"{name} operates in {industry} and serves its traditional market.",
        "technology_stack": "",
        "support_team_size": random.randint(0, 5),
        "funding": random.choice(["Bootstrap", "Grant", "None"]),
        "expected_tier": "Low",
    })

# Write accounts CSV
ACC_FIELDS = ["account_id", "name", "industry", "country", "employee_count",
              "description", "technology_stack", "support_team_size", "funding", "expected_tier"]
with open(OUT_DIR / "eval_accounts.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=ACC_FIELDS)
    w.writeheader()
    w.writerows(ACCOUNTS)
print(f"Wrote {len(ACCOUNTS)} accounts to data/eval/eval_accounts.csv")

# ---------------------------------------------------------------------------
# eval_signals.csv — 60 labeled signals (42 supported, 18 unsupported)
# ---------------------------------------------------------------------------

# Use first 20 account IDs for signals
SIGNAL_ACCT_IDS = [a["account_id"] for a in ACCOUNTS[:20]]

# (signal_type, raw_text_supported, raw_text_unsupported)
SIGNAL_TEMPLATES = {
    "support_hiring": {
        "supported": [
            "The company is actively recruiting customer support specialists and hiring for their growing support team.",
            "Job postings show they are recruiting 10 new support team members this quarter.",
            "HR announcements confirm the company is expanding its customer success headcount significantly.",
        ],
        "unsupported": [
            "The company announced a new product line targeting enterprise clients.",
            "Revenue grew by 30% last year according to the annual report.",
            "The CEO gave a keynote on digital transformation strategy.",
        ],
    },
    "funding": {
        "supported": [
            "The company raised $45 million in a Series B funding round led by Accel Partners.",
            "Investment announcement: $20M round closed to accelerate go-to-market expansion.",
            "The startup secured $15 million in a Series A investment from top-tier VCs.",
        ],
        "unsupported": [
            "The team held their annual company picnic last weekend.",
            "New office space opened in the downtown area.",
            "The company celebrated its 10th anniversary milestone.",
        ],
    },
    "product_launch": {
        "supported": [
            "The company announced the launch of its new AI-powered customer portal last month.",
            "New product release: the team introduced an automated ticketing system to the market.",
            "Press release confirms the company released a major platform update introducing three new features.",
        ],
        "unsupported": [
            "The company hired a new head of human resources.",
            "The annual sales conference was held in Las Vegas this year.",
            "Employee satisfaction scores reached an all-time high according to internal surveys.",
        ],
    },
    "rapid_growth": {
        "supported": [
            "The company reported 200% growth in ARR over the past 12 months, doubling its customer base.",
            "Headcount expanded from 50 to 150 employees in just 18 months, scaling operations rapidly.",
            "Customer base grew from 200 to 800 clients, showing exceptional expansion momentum.",
        ],
        "unsupported": [
            "The company rebranded its logo and updated its website color scheme.",
            "The CFO gave a presentation about budget planning for the upcoming fiscal year.",
            "Office renovation was completed ahead of schedule.",
        ],
    },
    "relevant_technology": {
        "supported": [
            "The company uses Zendesk for customer support and Salesforce for CRM integration.",
            "Job postings confirm the team runs Intercom alongside Jira for issue tracking workflows.",
            "Tech stack review shows Freshdesk is their primary helpdesk platform.",
        ],
        "unsupported": [
            "The company operates in the traditional retail sector with physical store locations.",
            "Manufacturing operations are handled by legacy ERP systems.",
            "The organization relies on spreadsheets for most of its internal reporting.",
        ],
    },
    "international_expansion": {
        "supported": [
            "The company announced international expansion into European markets with two new offices.",
            "Press release: the company is expanding globally with launches in EMEA and APAC.",
            "New regional headquarters opened to support growth across Asian markets.",
        ],
        "unsupported": [
            "The company focuses exclusively on its hometown market with no plans for growth.",
            "The board approved a cost-cutting initiative focused on domestic operations.",
            "The team participated in a local charity fundraiser event.",
        ],
    },
    "executive_change": {
        "supported": [
            "The company appointed a new CEO with a background in enterprise SaaS growth.",
            "LinkedIn announcement: a new VP of Customer Experience joined from Salesforce.",
            "Executive hire: new CTO hired to lead the engineering and product organization.",
        ],
        "unsupported": [
            "The company's marketing team produced a new brand video.",
            "Quarterly earnings call discussed routine operational metrics.",
            "The company was mentioned in a roundup article about industry trends.",
        ],
    },
}

SIGNALS = []
sid = 1
acct_cycle = 0

# Build supported pool: 6 per signal type x 7 types = 42
SUPPORTED_POOL = []
for sig_type, texts in SIGNAL_TEMPLATES.items():
    base = texts["supported"]
    variants = [
        f"Recent update: {base[0]}",
        f"Sources confirm: {base[1]}",
        f"Industry report: {base[2]}",
    ]
    SUPPORTED_POOL.extend([(sig_type, t) for t in base + variants])

# Build unsupported pool: exactly 18 (3+3+3+2+3+2+2 across 7 types)
UNSUPPORTED_POOL = []
counts_per_type = [3, 3, 3, 2, 3, 2, 2]
for (sig_type, texts), cnt in zip(SIGNAL_TEMPLATES.items(), counts_per_type):
    for t in texts["unsupported"][:cnt]:
        UNSUPPORTED_POOL.append((sig_type, t))

for sig_type, raw in SUPPORTED_POOL:
    acct_id = SIGNAL_ACCT_IDS[acct_cycle % len(SIGNAL_ACCT_IDS)]
    acct_cycle += 1
    age = random.randint(1, 60)
    SIGNALS.append({
        "signal_id": sid, "account_id": acct_id, "signal_type": sig_type,
        "raw_text": raw,
        "source": random.choice(["LinkedIn", "TechCrunch", "Press Release", "JobPosting", "CrunchBase"]),
        "date": days_ago(age), "is_supported": True,
    })
    sid += 1

for sig_type, raw in UNSUPPORTED_POOL:
    acct_id = SIGNAL_ACCT_IDS[acct_cycle % len(SIGNAL_ACCT_IDS)]
    acct_cycle += 1
    age = random.randint(90, 180)
    SIGNALS.append({
        "signal_id": sid, "account_id": acct_id, "signal_type": sig_type,
        "raw_text": raw,
        "source": random.choice(["Blog", "Internal", "Unknown", "Social"]),
        "date": days_ago(age), "is_supported": False,
    })
    sid += 1

random.shuffle(SIGNALS)
# Re-assign signal_ids after shuffle
for i, s in enumerate(SIGNALS):
    s["signal_id"] = i + 1

SIG_FIELDS = ["signal_id", "account_id", "signal_type", "raw_text", "source", "date", "is_supported"]
with open(OUT_DIR / "eval_signals.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=SIG_FIELDS)
    w.writeheader()
    w.writerows(SIGNALS)
print(f"Wrote {len(SIGNALS)} signals to data/eval/eval_signals.csv")
print(f"  Supported: {sum(1 for s in SIGNALS if s['is_supported'])}")
print(f"  Unsupported: {sum(1 for s in SIGNALS if not s['is_supported'])}")

import csv
import random
from datetime import datetime, timedelta
from pathlib import Path

def generate_signals_csv():
    random.seed(42)
    output_path = Path(__file__).parent.parent / "data" / "signals.csv"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    headers = ["account", "raw_text", "source", "date"]
    
    # Base accounts (these exist in our accounts.csv)
    accounts = [
        "Company 42 Cloud", "Company 46 Software", "Acme Technologies",
        "Nexus Cloud Systems", "Fintech Pulse Inc", "Global Logistics Ltd",
        "Micro Design Studio"
    ]
    
    # Every note must name a real account, or ingestion silently drops it.
    accounts_path = Path(__file__).parent.parent / "data" / "accounts.csv"
    with open(accounts_path, encoding="utf-8", newline="") as f:
        account_rows = list(csv.DictReader(f))
    hiring_account = next(r["company"] for r in account_rows if r["company"].startswith("Company") and r["industry"] == "B2B SaaS")
    named = set(accounts) | {hiring_account}
    pool = sorted(r["company"] for r in account_rows if r["company"] not in named)

    signals = []
    # Fixed reference date keeps the file reproducible; the demo seeder re-anchors dates to today.
    now = datetime(2026, 10, 2, 14, 7, 33)

    # 1. Tricky case: Vague text (should NOT extract a signal if strictly following facts)
    signals.append({
        "account": "Acme Technologies",
        "raw_text": "Acme Technologies is looking into expanding its horizons. We might see some changes next year.",
        "source": "Tech Blog",
        "date": now.strftime("%Y-%m-%dT%H:%M:%SZ")
    })

    # 2. Tricky case: Contradictory text
    signals.append({
        "account": "Acme Technologies",
        "raw_text": "Rumors suggested Acme was hiring for a massive support team expansion, but their CEO recently confirmed a hiring freeze for all non-engineering roles.",
        "source": "News Article",
        "date": now.strftime("%Y-%m-%dT%H:%M:%SZ")
    })

    # 3. Tricky case: Stale date (older than 180 days -> will be filtered/zeroed by SignalEngine decay)
    signals.append({
        "account": "Nexus Cloud Systems",
        "raw_text": "Nexus Cloud Systems successfully raised $20M in Series A funding to scale their platform.",
        "source": "Press Release",
        "date": (now - timedelta(days=200)).strftime("%Y-%m-%dT%H:%M:%SZ")
    })

    # 4. Tricky case: No real signal (just noise)
    signals.append({
        "account": "Micro Design Studio",
        "raw_text": "Micro Design Studio updated their website colors and logo.",
        "source": "Company Website",
        "date": now.strftime("%Y-%m-%dT%H:%M:%SZ")
    })

    # 5. Clear signal: Product launch & International expansion
    signals.append({
        "account": "Fintech Pulse Inc",
        "raw_text": "Fintech Pulse Inc just launched their new AI-driven product and announced plans to expand into Europe.",
        "source": "TechCrunch",
        "date": (now - timedelta(days=10)).strftime("%Y-%m-%dT%H:%M:%SZ")
    })

    # 6. Clear signal: Hiring support
    signals.append({
        "account": hiring_account,
        "raw_text": "We are hiring 50 new support staff to handle our increasing customer base.",
        "source": "Job Board",
        "date": (now - timedelta(days=30)).strftime("%Y-%m-%dT%H:%M:%SZ")
    })

    # Generate more random ones for the rest
    for acc in random.sample(pool, 60):
        text = random.choice([
            "Announced a new Series B funding round of $50M.",
            "Expanding their customer support team rapidly to meet demand.",
            "Released a major update to their core platform.",
            "Opening new offices in London and Tokyo for international expansion.",
            "Just hired a new Chief Revenue Officer to drive growth.",
            "Attended a trade show last week and gave away branded pens.", # Noise
            "We are not hiring right now." # Contradictory/No signal
        ])
        signals.append({
            "account": acc,
            "raw_text": text,
            "source": random.choice(["LinkedIn", "News", "Press Release", "Job Board"]),
            "date": (now - timedelta(days=random.randint(1, 200))).strftime("%Y-%m-%dT%H:%M:%SZ")
        })

    with open(output_path, mode="w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        for s in signals:
            writer.writerow(s)
            
    print(f"Generated {len(signals)} signals in {output_path}")

if __name__ == "__main__":
    generate_signals_csv()

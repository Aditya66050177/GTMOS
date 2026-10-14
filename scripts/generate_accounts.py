import csv
import random
from pathlib import Path


def generate_accounts_csv():
    """
    Generates 150 clearly synthetic demo accounts.
    Acme Technologies is hand-crafted to score ~87 (Priority 2):
      - Exact ICP industry + pain match  → 30/30
      - Employees 240, range 50-500      → 20/20
      - Zendesk only (1 of 5 ICP techs) → 4.5/15
      - Series B + 20 support staff     → 20/20
      - Country US                       → 15/15
      Total: 89.5  (Priority 2 / ~87 target)
    Distribution design:
      ~20% good-fit  → Priority 1/2
      ~25% medium    → Priority 2/3
      ~55% bad-fit   → Low
    """
    random.seed(42)
    output_path = Path(__file__).parent.parent / "data" / "accounts.csv"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    headers = [
        "company", "domain", "industry", "employees", "country",
        "technologies", "funding", "description", "support_team_size"
    ]

    hand_crafted = [
        # Acme: target ~87. Only 1 matching ICP tech (Zendesk), so tech_fit ≈ 4.5
        {
            "company": "Acme Technologies",
            "domain": "acme.com",
            "industry": "B2B SaaS",
            "employees": 240,
            "country": "US",
            "technologies": "Zendesk;Oracle;Workday",
            "funding": "Series B",
            "description": "B2B SaaS customer platform experiencing high support ticket volume and help desk overload.",
            "support_team_size": 20
        },
        # Nexus: good-fit, Series A intent
        {
            "company": "Nexus Cloud Systems",
            "domain": "nexuscloud.io",
            "industry": "Software",
            "employees": 120,
            "country": "US",
            "technologies": "Intercom;Jira;AWS",
            "funding": "Series A",
            "description": "Cloud infrastructure provider solving slow response time and scaling support operations.",
            "support_team_size": 15
        },
        # Fintech Pulse: good-fit, full tech overlap
        {
            "company": "Fintech Pulse Inc",
            "domain": "fintechpulse.com",
            "industry": "Cloud Services",
            "employees": 310,
            "country": "US",
            "technologies": "Freshdesk;Zendesk;Salesforce",
            "funding": "Series C",
            "description": "Financial tech platform facing high support costs and ticket volume.",
            "support_team_size": 30
        },
        # Deliberate bad fit: wrong industry + too big + wrong country
        {
            "company": "Global Logistics Ltd",
            "domain": "globallogistics.co.uk",
            "industry": "Logistics",
            "employees": 1200,
            "country": "UK",
            "technologies": "Oracle;SAP",
            "funding": "Public",
            "description": "Freight forwarding and supply chain solutions.",
            "support_team_size": 50
        },
        # Deliberate bad fit: too small + wrong industry
        {
            "company": "Micro Design Studio",
            "domain": "microdesign.net",
            "industry": "Design",
            "employees": 8,
            "country": "US",
            "technologies": "Figma;Slack",
            "funding": "Bootstrapped",
            "description": "Bespoke web design agency.",
            "support_team_size": 1
        }
    ]

    icp_industries = ["B2B SaaS", "Software", "Cloud Services"]
    non_icp_industries = ["Healthcare", "E-commerce", "Manufacturing", "Retail", "Education", "Logistics"]
    icp_countries = ["US", "United States"]
    non_icp_countries = ["Germany", "France", "Australia", "India", "Brazil", "Japan"]
    other_countries = ["UK", "Canada"]
    tech_pool = ["Zendesk", "Intercom", "Salesforce", "Freshdesk", "Jira",
                 "HubSpot", "Slack", "AWS", "Datadog", "Marketo", "Stripe", "Workday"]
    icp_techs = ["Zendesk", "Intercom", "Salesforce", "Freshdesk", "Jira"]

    good_descs = [
        "SaaS platform reducing help desk overload and high support ticket volume.",
        "Cloud software suite addressing high support costs and slow response time.",
        "Software vendor seeking to lower support costs and improve response times.",
        "Digital platform facing help desk overload and growing support ticket volume.",
    ]
    bad_descs = [
        "Retail management software focusing on inventory automation.",
        "Industrial manufacturing enterprise platform.",
        "Online learning and education services portal.",
        "E-commerce storefront builder for boutique retailers.",
        "Healthtech patient engagement workflow solution.",
        "Regional logistics and fleet tracking software provider.",
    ]

    accounts = list(hand_crafted)

    for i in range(1, 146):
        rng = random.random()

        if rng < 0.18:
            # Good fit → Priority 1/2
            ind = random.choice(icp_industries)
            cntry = random.choice(icp_countries)
            emp = random.randint(50, 500)
            techs = random.sample(icp_techs, k=random.randint(2, 4))
            desc = random.choice(good_descs)
            supp = random.randint(15, 40)
            funding = random.choice(["Series B", "Series C", "Growth"])

        elif rng < 0.42:
            # Medium fit → Priority 2/3
            ind = random.choice(icp_industries + ["Cybersecurity", "Fintech"])
            cntry = random.choice(icp_countries + other_countries)
            emp = random.choice([
                random.randint(38, 49),     # just outside min boundary
                random.randint(50, 500),    # in range
                random.randint(501, 600),   # just over max
            ])
            techs = random.sample(tech_pool, k=random.randint(1, 2))
            desc = random.choice(good_descs + bad_descs)
            supp = random.randint(5, 20)
            funding = random.choice(["Series A", "Seed", "Series B"])

        else:
            # Bad fit → Low
            ind = random.choice(non_icp_industries)
            cntry = random.choice(non_icp_countries)
            emp = random.choice([
                random.randint(1, 30),
                random.randint(800, 5000),
            ])
            techs = random.sample(tech_pool, k=random.randint(0, 1))
            desc = random.choice(bad_descs)
            supp = random.randint(0, 8)
            funding = random.choice(["Bootstrapped", "Seed"])

        domain_suffix = random.choice([".com", ".io", ".net", ".org", ".co"])
        company_name = f"Company {i} {ind.split()[0]}"
        domain_name = f"company{i}{ind.split()[0].lower()}{domain_suffix}"

        accounts.append({
            "company": company_name,
            "domain": domain_name,
            "industry": ind,
            "employees": emp,
            "country": cntry,
            "technologies": ";".join(techs) if techs else "",
            "funding": funding,
            "description": desc,
            "support_team_size": supp
        })

    with open(output_path, mode="w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        for acc in accounts:
            writer.writerow(acc)

    print(f"Generated {len(accounts)} synthetic accounts at {output_path}")


if __name__ == "__main__":
    generate_accounts_csv()

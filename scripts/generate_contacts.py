import csv
import random
from pathlib import Path

def generate_contacts_csv():
    random.seed(42)
    output_path = Path(__file__).parent.parent / "data" / "contacts.csv"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    headers = ["company", "name", "role", "email", "linkedin_url"]
    
    first_names = ["Sarah", "Michael", "David", "Jessica", "Alex", "Emily", "James", "Rachel", "Daniel", "Lisa", "Robert", "Elena", "Carlos", "Priya", "Marcus"]
    last_names = ["Chen", "Smith", "Johnson", "Miller", "Davis", "Wilson", "Taylor", "Anderson", "Patel", "Garcia", "Kim", "Martinez", "Robinson", "Clark", "Lewis"]
    
    buyer_roles = [
        "VP of Customer Support",
        "Head of Customer Experience",
        "Chief Revenue Officer",
        "Head of Product",
        "VP Sales",
        "Director of Support Operations",
        "Customer Success Lead"
    ]
    
    # Read companies from data/accounts.csv
    accounts_path = Path(__file__).parent.parent / "data" / "accounts.csv"
    companies = []
    if accounts_path.exists():
        with open(accounts_path, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                comp = row.get("company", "").strip()
                domain = row.get("domain", "").strip()
                if comp:
                    companies.append((comp, domain))
    else:
        companies = [
            ("Acme Technologies", "acmetechnologies.com"),
            ("Fintech Pulse Inc", "fintechpulse.com"),
            ("Nexus Cloud Systems", "nexuscloud.io")
        ]

    # Target top 50 accounts + named accounts with 1-2 contacts each
    contacts = [
        {
            "company": "Acme Technologies",
            "name": "Sarah Chen",
            "role": "VP of Customer Support",
            "email": "sarah.chen@acmetechnologies.com",
            "linkedin_url": "https://linkedin.com/in/sarah-chen-cx"
        },
        {
            "company": "Acme Technologies",
            "name": "David Miller",
            "role": "Chief Revenue Officer",
            "email": "david.miller@acmetechnologies.com",
            "linkedin_url": "https://linkedin.com/in/david-miller-cro"
        },
        {
            "company": "Fintech Pulse Inc",
            "name": "Elena Rostova",
            "role": "Head of Customer Experience",
            "email": "elena.rostova@fintechpulse.com",
            "linkedin_url": "https://linkedin.com/in/elena-rostova-fintech"
        },
        {
            "company": "Nexus Cloud Systems",
            "name": "Marcus Vance",
            "role": "VP of Customer Support",
            "email": "marcus.vance@nexuscloud.io",
            "linkedin_url": "https://linkedin.com/in/marcus-vance-nexus"
        }
    ]

    used_companies = {"Acme Technologies", "Fintech Pulse Inc", "Nexus Cloud Systems"}

    for comp, domain in companies[:50]:
        if comp in used_companies:
            continue
        clean_domain = domain if domain else f"{comp.lower().replace(' ', '')}.com"
        # Add 1-2 contacts
        num_contacts = random.choice([1, 2])
        for _ in range(num_contacts):
            fname = random.choice(first_names)
            lname = random.choice(last_names)
            full_name = f"{fname} {lname}"
            role = random.choice(buyer_roles)
            email = f"{fname.lower()}.{lname.lower()}@{clean_domain}"
            linkedin = f"https://linkedin.com/in/{fname.lower()}-{lname.lower()}"
            contacts.append({
                "company": comp,
                "name": full_name,
                "role": role,
                "email": email,
                "linkedin_url": linkedin
            })

    with open(output_path, mode="w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        for c in contacts:
            writer.writerow(c)

    print(f"Generated {len(contacts)} contacts in {output_path}")

if __name__ == "__main__":
    generate_contacts_csv()

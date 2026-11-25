"""Rewrite identity fields in the demo CSVs so nobody can mistake them for real people.

Only identity fields change:
  * data/accounts.csv  -> domain becomes <company-slug>.example
  * data/contacts.csv  -> clearly fictional names, emails at the account's .example
                          domain, and LinkedIn URLs on the non-resolving
                          linkedin.example host
Company names, industries, sizes, tech stacks and every scoring input stay the same,
so scores and tiers do not move.

`.example` is reserved by RFC 2606 and can never be registered, so these
addresses cannot reach anyone. The script is deterministic and idempotent.

Usage (from the project root):
    python scripts/fictionalize_demo_data.py
"""
import csv
import re
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data"

# Surnames chosen to read as obviously invented.
FICTIONAL_SURNAMES = [
    "Placeholder", "Sampleton", "Demoson", "Testwell", "Mockford", "Fakely",
    "Exampleby", "Prototyp", "Stubbs-Fictional", "Notreal", "Dummington", "Pretendo",
]
FIRST_NAMES = [
    "Ada", "Blake", "Casey", "Dana", "Ellis", "Frankie", "Gray", "Harper",
    "Indy", "Jules", "Kai", "Lane", "Morgan", "Noor", "Oakley", "Parker",
]


def slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def fictional_domain(company: str) -> str:
    return f"{slug(company)}.example"


def fictional_name(index: int) -> str:
    first = FIRST_NAMES[index % len(FIRST_NAMES)]
    last = FICTIONAL_SURNAMES[(index // len(FIRST_NAMES) + index) % len(FICTIONAL_SURNAMES)]
    return f"{first} {last}"


def _read(path: Path):
    with open(path, encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        return reader.fieldnames, list(reader)


def _write(path: Path, fieldnames, rows) -> None:
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def fictionalize(data_dir: Path = DATA) -> dict:
    acc_fields, accounts = _read(data_dir / "accounts.csv")
    for row in accounts:
        row["domain"] = fictional_domain(row["company"])
    _write(data_dir / "accounts.csv", acc_fields, accounts)

    con_fields, contacts = _read(data_dir / "contacts.csv")
    for i, row in enumerate(contacts):
        name = fictional_name(i)
        handle = slug(name)
        row["name"] = name
        row["email"] = f"{handle.replace('-', '.')}@{fictional_domain(row['company'])}"
        row["linkedin_url"] = f"https://linkedin.example/in/{handle}-{i}"
    _write(data_dir / "contacts.csv", con_fields, contacts)
    return {"accounts": len(accounts), "contacts": len(contacts)}


if __name__ == "__main__":
    counts = fictionalize()
    print(f"Fictionalized {counts['accounts']} accounts and {counts['contacts']} contacts.")

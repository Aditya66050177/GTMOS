"""
scripts/ask_three_questions.py
Demonstrates the AI Analyst by asking three GTM questions and printing
the routed function, explanation, and key data used.
Windows-safe: no emojis.
"""
import sys
import io
import json
from pathlib import Path

# Force UTF-8 stdout for Windows
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.database import SessionLocal
from app.db.init_db import init_db
from app.services.analyst_service import AnalystService
from app.ai.llm import LLMService


QUESTIONS = [
    "Why are meetings declining?",
    "Which industry replies most?",
    "What is my conversion from contacted to replied?",
]


def ask_all():
    init_db()
    db = SessionLocal()
    analyst = AnalystService(llm=LLMService(mode="mock"))

    print("=" * 70)
    print("AI GTM ANALYST - THREE QUESTION DEMO")
    print("=" * 70)

    for i, question in enumerate(QUESTIONS, 1):
        print()
        print(f"QUESTION {i}: {question}")
        print("-" * 60)

        result = analyst.ask(db, question)

        print(f"  Function Called : {result.function_called}")
        print()
        print(f"  Explanation:")
        # Wrap long explanation lines at 80 chars
        import textwrap
        for line in textwrap.wrap(result.explanation, width=80):
            print(f"    {line}")
        print()
        print(f"  Data Used (summary):")

        # Pretty-print the top-level keys and first few values
        if isinstance(result.data, dict):
            for key, val in result.data.items():
                if isinstance(val, list):
                    print(f"    [{key}] ({len(val)} items):")
                    for item in val[:5]:
                        print(f"      - {json.dumps(item)}")
                    if len(val) > 5:
                        print(f"      ... and {len(val) - 5} more")
                elif isinstance(val, dict):
                    print(f"    [{key}]: {json.dumps(val)[:200]}")
                else:
                    print(f"    [{key}]: {val}")
        else:
            print(f"    {result.data}")

        print()

    db.close()
    print("=" * 70)
    print("DONE")
    print("=" * 70)


if __name__ == "__main__":
    ask_all()

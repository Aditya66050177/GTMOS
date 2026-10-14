"""
Tiny live-call verification for the Gemini provider.
Usage: python scripts/verify_gemini_live.py

Reads LLM_API_KEY from .env (never prints or logs it).
Makes one structured call to Gemini and prints latency + token usage.
"""
import sys, io, os, time
from pathlib import Path

# Windows encoding safety
if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

from pydantic import BaseModel
from typing import List


class TinyTestSchema(BaseModel):
    company_name: str
    industry: str
    employee_count: int
    top_competitors: List[str]


def main():
    api_key = os.getenv("LLM_API_KEY", "")
    if not api_key.strip():
        print("[ERROR] LLM_API_KEY not set in .env. Cannot run live verification.")
        sys.exit(1)

    # Confirm key is loaded (never print it!)
    print(f"[OK] LLM_API_KEY loaded ({len(api_key)} chars, starts with {api_key[:4]}...)")

    from app.ai.llm import LLMService

    svc = LLMService(
        mode="live",
        api_key=api_key,
        provider="gemini",
        model=os.getenv("LLM_MODEL", "gemini-2.0-flash"),
    )

    prompt = (
        "Provide factual information about Acme Corp, "
        "a fictional B2B SaaS company in the customer support space. "
        "Return company_name, industry, employee_count, and top_competitors."
    )

    print(f"\n--- Calling Gemini ({svc.model}) ---")
    t0 = time.monotonic()
    try:
        result = svc.generate_structured(prompt, TinyTestSchema)
        t1 = time.monotonic()
    except Exception as e:
        print(f"[FAIL] Live call failed: {e}")
        sys.exit(1)

    print(f"[OK] Live call succeeded!")
    print(f"\n--- Response ---")
    print(f"  company_name:     {result.company_name}")
    print(f"  industry:         {result.industry}")
    print(f"  employee_count:   {result.employee_count}")
    print(f"  top_competitors:  {result.top_competitors}")
    print(f"\n--- Metrics ---")
    print(f"  Wall-clock time:  {(t1 - t0) * 1000:.0f} ms")
    print(f"  SDK latency:      {svc.last_latency_ms} ms")
    print(f"  Prompt tokens:    {svc.last_prompt_tokens}")
    print(f"  Output tokens:    {svc.last_candidates_tokens}")
    print(f"  Total tokens:     {svc.last_total_tokens}")
    print(f"\n[PASS] Gemini live provider is working correctly.")


if __name__ == "__main__":
    main()

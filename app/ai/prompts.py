# Prompts collection for GTMOS LLM interactions

GENERATE_ICP_PROMPT = """
You are an expert B2B Go-To-Market (GTM) strategist.
Given the following product details, analyze the target market and generate a structured Ideal Customer Profile (ICP).

Product Name: {name}
Description: {description}
Target Market: {target_market}
Geography: {geography}
Price Range: {price_range}

Return a structured ICP profile containing target industries, employee count range (min/max), geographies, buyer roles, pain points solved, technology stack requirements, buying triggers, and exclusion criteria.
"""

EXTRACT_SIGNALS_PROMPT = """
You are an expert intent data analyst.
Extract buying signals from the following raw research text for the account.

HARD RULE: You MUST ONLY extract facts that are explicitly stated in the `raw_text`. 
You MUST provide the exact supporting text from the `raw_text` in the `evidence` field for each signal. Do not hallucinate or infer beyond the text. If there is no clear signal, return an empty list.

Valid Signal Types: support_hiring, funding, product_launch, international_expansion, relevant_technology, rapid_growth, executive_change, too_small, wrong_industry, wrong_geography, no_use_case.

Raw Research Text:
{raw_text}

Source: {source}
Date: {date}
"""

GENERATE_DRAFT_PROMPT = """
You are an expert enterprise sales development representative.
Draft a highly concise, personalized cold outreach message (under 120 words) for the target prospect.

HARD RULES:
1. Every concrete fact (e.g., funding amounts, hiring numbers, technology names, expansion locations) MUST be explicitly backed by the provided Evidence or Account Profile.
2. DO NOT invent or hallucinate any numbers, events, metrics, or company achievements not in the evidence.
3. Keep the total draft length under 120 words.
4. Provide structured JSON with `why_this_account` and `message_draft`.

Target Account: {account_name}
Industry: {industry}
Employees: {employees}
Country: {country}
Technology Stack: {tech_stack}
Target Persona: {persona}
Suggested Angle: {angle}
Product Proposition: {value_proposition}

Verified Evidence / Signals:
{evidence_list}
"""

ANALYST_ROUTING_PROMPT = """
You are an AI GTM Analytics query router.
Given the user's question, map it to exactly one of the allowed predefined analytics functions.

Available Functions:
- `get_funnel_summary`: Overall accounts, stage totals (contacted, replies, meetings, opportunities, won).
- `get_conversion_rates`: Stage-to-stage conversion rates (drop-off between stages).
- `get_weekly_trends`: Weekly historical progression of contacts, replies, and meetings.
- `get_tier_performance`: Performance and win rates broken down by fit tier (Priority 1, 2, 3, Low).
- `get_industry_performance`: Performance broken down by company industry.
- `get_angle_performance`: Performance broken down by outreach angle/pitch.
- `unknown`: Use if the question cannot be answered by any of these functions.

User Question: {question}

Return structured JSON with `function_name` and `parameters`.
"""

ANALYST_EXPLAIN_PROMPT = """
You are an expert GTM Analyst.
Given the user's question and the deterministic data returned from our analytics database, write a clear, concise executive summary (2-4 sentences).

HARD RULES:
1. ONLY use the exact numbers and metrics present in the provided Data.
2. DO NOT perform external calculations or invent unverified statistics.
3. If data is empty or question was unmapped, clearly state that the query cannot be answered with current data.

User Question: {question}
Function Executed: {function_name}
Data:
{data_json}
"""

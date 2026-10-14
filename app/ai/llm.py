import json
import logging
import time
from typing import Type, TypeVar, Any, Dict, get_origin, get_args, Union, Optional
from pydantic import BaseModel, ValidationError
from app.core.config import settings

T = TypeVar("T", bound=BaseModel)
logger = logging.getLogger(__name__)

# Rate-limit delay (seconds) between live LLM calls.
# Prevents hitting the free-tier quota on Google Gemini.
GEMINI_CALL_DELAY_SECS: float = 1.5

# Track when the last live call was made (module-level) so the delay
# is applied across all LLMService instances in the same process.
_last_live_call_ts: float = 0.0


class LLMService:
    def __init__(self, mode: Optional[str] = None, api_key: Optional[str] = None,
                 provider: Optional[str] = None, model: Optional[str] = None):
        self.mode = mode if mode is not None else settings.LLM_MODE
        self.api_key = api_key if api_key is not None else settings.LLM_API_KEY
        self.provider = provider if provider is not None else settings.LLM_PROVIDER
        self.model = model if model is not None else settings.LLM_MODEL

        # Metrics from the most recent live call
        self.last_latency_ms: Optional[float] = None
        self.last_prompt_tokens: Optional[int] = None
        self.last_candidates_tokens: Optional[int] = None
        self.last_total_tokens: Optional[int] = None

    # ------------------------------------------------------------------
    # Mock helpers (unchanged from original)
    # ------------------------------------------------------------------

    def _generate_mock_value(self, field_type: Any, field_name: str) -> Any:
        origin = get_origin(field_type)
        args = get_args(field_type)

        if origin is Union:
            non_none_args = [arg for arg in args if arg is not type(None)]
            if non_none_args:
                return self._generate_mock_value(non_none_args[0], field_name)

        if isinstance(field_type, type) and issubclass(field_type, BaseModel):
            return self._build_mock_data(field_type)

        if origin is list or field_type is list:
            item_type = args[0] if args else str
            return [self._generate_mock_value(item_type, field_name)]

        if origin is dict or field_type is dict:
            return {"mock_key": "mock_value"}

        if field_type is int:
            return 10
        if field_type is float:
            return 0.85
        if field_type is bool:
            return True
        if field_type is str:
            clean_name = field_name.replace("_", " ").title()
            return f"Mock {clean_name}"

        return "Mock Value"

    def _build_mock_data(self, schema: Type[T], prompt: str = "") -> Dict[str, Any]:
        if schema.__name__ == "ICPProfileSchema":
            return {
                "industries": ["B2B SaaS", "Software", "Cloud Services"],
                "min_employees": 50,
                "max_employees": 500,
                "geographies": ["US", "United States", "North America"],
                "buyer_roles": ["VP of Customer Support", "Head of Customer Experience", "Chief Revenue Officer"],
                "pain_points": ["High support ticket volume", "Slow response time", "High support costs", "Help desk overload"],
                "technologies": ["Zendesk", "Intercom", "Salesforce", "Freshdesk", "Jira"],
                "buying_triggers": ["Hiring support staff", "New funding round", "Scaling customer base"],
                "exclusion_criteria": ["B2C Only", "Government", "Hardware manufacturing"]
            }

        if schema.__name__ == "SignalListSchema":
            signals = []
            prompt_lower = prompt.lower()
            if "hiring" in prompt_lower or "support team" in prompt_lower:
                signals.append({"type": "support_hiring", "description": "Hiring support staff", "strength": 0.8, "source": "MockSource", "detected_at": "2023-01-01T00:00:00Z", "confidence": 0.9, "evidence": "hiring 50 new support staff" if "hiring 50 new support staff" in prompt_lower else ("expanding their customer support team" if "expanding their customer support team" in prompt_lower else "hiring")})
            if "funding" in prompt_lower or "raised" in prompt_lower or "series" in prompt_lower:
                signals.append({"type": "funding", "description": "Raised funding", "strength": 0.9, "source": "MockSource", "detected_at": "2023-01-01T00:00:00Z", "confidence": 0.9, "evidence": "series a funding" if "series a funding" in prompt_lower else ("series b funding" if "series b funding" in prompt_lower else "raised")})
            if "launch" in prompt_lower or "release" in prompt_lower:
                signals.append({"type": "product_launch", "description": "Launched new product", "strength": 0.7, "source": "MockSource", "detected_at": "2023-01-01T00:00:00Z", "confidence": 0.8, "evidence": "launched their new ai-driven product" if "launched their new ai-driven product" in prompt_lower else ("released a major update" if "released a major update" in prompt_lower else "launch")})
            if "expand" in prompt_lower or "europe" in prompt_lower or "asia" in prompt_lower:
                signals.append({"type": "international_expansion", "description": "Expanding internationally", "strength": 0.8, "source": "MockSource", "detected_at": "2023-01-01T00:00:00Z", "confidence": 0.85, "evidence": "expand into europe" if "expand into europe" in prompt_lower else ("new offices in london and tokyo" if "new offices in london and tokyo" in prompt_lower else "expand")})

            return {"signals": signals}

        if schema.__name__ == "PersonalizationOutputSchema":
            account_name = "your team"
            for line in prompt.split("\n"):
                if line.startswith("Target Account:"):
                    account_name = line.replace("Target Account:", "").strip()
                    break

            return {
                "why_this_account": f"{account_name} matches our ICP profile with strong buying intent and active market growth.",
                "message_draft": f"Hi team, noticed {account_name}'s recent momentum. As you scale operations, our AI platform helps streamline ticket resolution and automate repetitive workflows without adding headcount. Would you be open to a brief 10-minute introductory chat next week?"
            }

        if schema.__name__ == "AnalystQueryIntentSchema":
            q_text = prompt.lower()
            if "user question:" in q_text:
                q_text = q_text.split("user question:", 1)[1]

            if any(k in q_text for k in ["conversion", "drop off", "stage to stage", "contacted to replied", "replied to meeting"]):
                return {"function_name": "get_conversion_rates", "parameters": {}}
            elif any(k in q_text for k in ["trend", "weekly", "week", "timeline", "trajectory", "over time", "declin", "meeting"]):
                return {"function_name": "get_weekly_trends", "parameters": {}}
            elif any(k in q_text for k in ["tier", "priority", "fit tier"]):
                return {"function_name": "get_tier_performance", "parameters": {}}
            elif any(k in q_text for k in ["industry", "sector", "vertical", "industries", "replies most"]):
                return {"function_name": "get_industry_performance", "parameters": {}}
            elif any(k in q_text for k in ["angle", "pitch", "message"]):
                return {"function_name": "get_angle_performance", "parameters": {}}
            elif any(k in q_text for k in ["funnel", "summary", "pipeline", "accounts", "how many", "overview", "total", "won"]):
                return {"function_name": "get_funnel_summary", "parameters": {}}
            else:
                return {"function_name": "unknown", "parameters": {}}

        if schema.__name__ == "AnalystExplanationSchema":
            return {
                "explanation": "Based on current GTM data, our pipeline demonstrates strong qualification momentum. The metrics extracted reflect verified activity counts across target accounts."
            }

        data = {}
        for field_name, field_info in schema.model_fields.items():
            if field_info.is_required():
                data[field_name] = self._generate_mock_value(field_info.annotation, field_name)
            elif field_info.default_factory is not None:
                data[field_name] = field_info.default_factory()
            else:
                data[field_name] = field_info.default
        return data

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate_structured(self, prompt: str, schema: Type[T]) -> T:
        """
        Generate structured output validated against a Pydantic schema.
        In mock mode: returns deterministic fixture data adhering to the schema.
        In live mode: calls the configured provider (default: Gemini), validates
        against the schema, retries once on validation failure.
        """
        if self.mode == "mock":
            mock_dict = self._build_mock_data(schema, prompt)
            return schema.model_validate(mock_dict)

        if not self.api_key or not self.api_key.strip():
            raise ValueError(
                "LLM_API_KEY is not set or empty. Cannot run in live mode. "
                "Set LLM_API_KEY in environment or use LLM_MODE=mock."
            )

        attempts = 2
        last_error = None

        for attempt in range(attempts):
            try:
                raw_json = self._call_live_provider(prompt, schema)
                data = json.loads(raw_json)
                return schema.model_validate(data)
            except NotImplementedError:
                raise
            except (ValidationError, json.JSONDecodeError, Exception) as e:
                logger.warning(f"Live LLM attempt {attempt + 1} failed: {e}")
                last_error = e
                if attempt == attempts - 1:
                    raise RuntimeError(
                        f"Failed to generate valid Pydantic response after {attempts} attempts. Error: {last_error}"
                    )

    # ------------------------------------------------------------------
    # Live provider dispatch
    # ------------------------------------------------------------------

    def _call_live_provider(self, prompt: str, schema: Type[T]) -> str:
        """Dispatch to the configured live LLM provider."""
        if self.provider == "gemini":
            return self._call_gemini(prompt, schema)
        raise NotImplementedError(
            f"Unsupported LLM_PROVIDER: {self.provider!r}. Supported: gemini"
        )

    def _call_gemini(self, prompt: str, schema: Type[T]) -> str:
        """
        Call the Google Gemini API using the google-genai SDK.
        Returns raw JSON string conforming to the schema.
        Applies a rate-limit delay between consecutive calls.
        Never prints or logs the API key.
        """
        global _last_live_call_ts

        try:
            from google import genai
            from google.genai import types
        except ImportError:
            raise ImportError(
                "google-genai package is required for live Gemini calls. "
                "Install it with: pip install google-genai"
            )

        # --- rate-limit delay ---
        now = time.time()
        elapsed = now - _last_live_call_ts
        if elapsed < GEMINI_CALL_DELAY_SECS:
            wait = GEMINI_CALL_DELAY_SECS - elapsed
            logger.debug(f"Rate-limit: sleeping {wait:.2f}s before Gemini call")
            time.sleep(wait)

        # Build the JSON schema from the Pydantic model
        json_schema = schema.model_json_schema()

        # Create the Gemini client
        client = genai.Client(api_key=self.api_key)

        # Construct the generation config requesting JSON output
        gen_config = types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=json_schema,
            temperature=0.2,
        )

        system_instruction = (
            "You are a B2B GTM (Go-To-Market) AI assistant. "
            "Respond ONLY with valid JSON matching the provided schema. "
            "No markdown, no code fences, just raw JSON."
        )

        start = time.monotonic()
        response = client.models.generate_content(
            model=self.model,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=json_schema,
                temperature=0.2,
                system_instruction=system_instruction,
            ),
        )
        end = time.monotonic()

        _last_live_call_ts = time.time()

        # Record metrics
        self.last_latency_ms = round((end - start) * 1000, 1)
        if hasattr(response, "usage_metadata") and response.usage_metadata:
            um = response.usage_metadata
            self.last_prompt_tokens = getattr(um, "prompt_token_count", None)
            self.last_candidates_tokens = getattr(um, "candidates_token_count", None)
            self.last_total_tokens = getattr(um, "total_token_count", None)
        else:
            self.last_prompt_tokens = None
            self.last_candidates_tokens = None
            self.last_total_tokens = None

        raw = response.text
        if not raw or not raw.strip():
            raise RuntimeError("Gemini returned empty response text")

        logger.info(
            "Gemini call: model=%s latency=%sms tokens=%s",
            self.model, self.last_latency_ms, self.last_total_tokens
        )
        return raw.strip()

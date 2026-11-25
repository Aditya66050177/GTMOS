from datetime import datetime

from pydantic import BaseModel, Field, field_validator


class ResearchRequest(BaseModel):
    raw_text: str = Field(..., min_length=1, max_length=5_000, description="Raw text of the research")
    source: str = Field(..., min_length=1, max_length=120, description="Source of the text")
    date_str: str = Field(..., max_length=40, description="ISO 8601 date string")

    @field_validator("date_str")
    @classmethod
    def must_be_iso_date(cls, value: str) -> str:
        try:
            datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError("date_str must be an ISO 8601 date, e.g. 2026-01-31") from exc
        return value

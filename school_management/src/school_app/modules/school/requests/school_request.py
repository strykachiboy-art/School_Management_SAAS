import re
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator

SLUG_PATTERN = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")


class SchoolBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=200)
    slug: str = Field(..., min_length=2, max_length=100)
    country: Optional[str] = Field(None, max_length=100)
    timezone: str = "UTC"
    currency: str = Field("USD", min_length=3, max_length=10)
    locale: str = Field("en", min_length=2, max_length=10)

    @field_validator("slug")
    @classmethod
    def slug_url_safe(cls, v: str) -> str:
        v = v.lower()
        if not SLUG_PATTERN.match(v):
            raise ValueError("slug must be lowercase letters, numbers, and single hyphens only (e.g. 'green-valley-academy')")
        return v


class SchoolCreateRequest(SchoolBase):
    pass


class SchoolUpdateRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=200)
    country: Optional[str] = Field(None, max_length=100)
    timezone: Optional[str] = None
    currency: Optional[str] = Field(None, min_length=3, max_length=10)
    locale: Optional[str] = Field(None, min_length=2, max_length=10)
    is_active: Optional[bool] = None
    onboarding_completed: Optional[bool] = None


class SchoolResponse(SchoolBase):
    id: int
    is_active: bool
    onboarding_completed: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
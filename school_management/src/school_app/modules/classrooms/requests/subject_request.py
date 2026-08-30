from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, field_validator


class SubjectBase(BaseModel):
    name: str
    code: str
    description: Optional[str] = None

    @field_validator("name")
    @classmethod
    def name_not_blank(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("name cannot be blank")
        return v

    @field_validator("code")
    @classmethod
    def code_format(cls, v: str) -> str:
        v = v.strip().upper()
        if not v.isalnum():
            raise ValueError("code must be alphanumeric with no spaces")
        return v


class SubjectCreateRequest(SubjectBase):
    pass


class SubjectResponse(SubjectBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
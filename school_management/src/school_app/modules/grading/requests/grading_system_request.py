from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from school_app.enums.grading import GradingStrategy


class GradingSystemBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    strategy: GradingStrategy = GradingStrategy.LETTER_GRADE
    is_default: bool = False
    school_id: Optional[int] = None


class GradingSystemCreateRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    strategy: GradingStrategy = GradingStrategy.LETTER_GRADE
    is_default: bool = False
    school_id: int

    @field_validator("strategy", mode="before")
    @classmethod
    def normalize_strategy(cls, value):
        """
        Accept both enum values and case-insensitive strings.

        Examples:
            LETTER_GRADE -> letter_grade
            Letter_Grade -> letter_grade
            letter_grade -> letter_grade
        """
        if isinstance(value, GradingStrategy):
            return value

        if isinstance(value, str):
            return value.strip().lower()

        return value


class GradingSystemUpdateRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    strategy: Optional[GradingStrategy] = None
    is_default: Optional[bool] = None
    is_active: Optional[bool] = None

    @field_validator("strategy", mode="before")
    @classmethod
    def normalize_strategy(cls, value):
        """
        Accept case-insensitive grading strategy values during updates.
        """
        if isinstance(value, GradingStrategy):
            return value

        if isinstance(value, str):
            return value.strip().lower()

        return value


class GradingSystemResponse(GradingSystemBase):
    id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
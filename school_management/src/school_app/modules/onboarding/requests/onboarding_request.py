from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field

from school_app.enums.onboarding import OnboardingStep
from school_app.enums.grading import GradingStrategy


# ============================== step 1: school info ==============================

class SchoolInfoStepRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=200)
    slug: Optional[str] = Field(None, min_length=2, max_length=100)
    country: Optional[str] = Field(None, max_length=100)


# ============================== step 2: localization ==============================

class LocalizationStepRequest(BaseModel):
    timezone: Optional[str] = None
    currency: Optional[str] = Field(None, min_length=3, max_length=10)
    locale: Optional[str] = Field(None, min_length=2, max_length=10)


# ============================== step 3: academic structure ==============================

class AcademicLevelInput(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    display_order: Optional[int] = None
    sections: List[str] = Field(default_factory=list)


class AcademicStageInput(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    code: Optional[str] = Field(None, max_length=10)
    display_order: Optional[int] = None
    levels: List[AcademicLevelInput] = Field(default_factory=list)


class AcademicStructureStepRequest(BaseModel):
    stages: List[AcademicStageInput] = Field(..., min_length=1)


# ============================== step 4: grading config ==============================

class GradingRuleInput(BaseModel):
    grade_name: str = Field(..., min_length=1, max_length=20)
    min_score: float
    max_score: Optional[float] = None
    grade_point: Optional[float] = None
    remark: Optional[str] = Field(None, max_length=100)
    display_order: Optional[int] = None


class GradingConfigStepRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    strategy: GradingStrategy = GradingStrategy.LETTER_GRADE
    rules: List[GradingRuleInput] = Field(..., min_length=1)


# ============================== step 5: promotion config ==============================

class PromotionRuleInput(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    from_level_name: str
    to_level_name: Optional[str] = None  # None = terminal level (graduation)
    min_average_score: Optional[float] = None
    min_attendance_percentage: Optional[float] = None
    min_subject_score: Optional[float] = None
    max_failed_subjects: Optional[int] = None
    requires_admin_approval: bool = False


class PromotionConfigStepRequest(BaseModel):
    rules: List[PromotionRuleInput] = Field(default_factory=list)


# ============================== step 6: admin account ==============================

class AdminAccountStepRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=30)
    email: str = Field(..., max_length=255)
    password: str = Field(..., min_length=8)


# ============================== response ==============================

class OnboardingProgressResponse(BaseModel):
    school_id: int
    current_step: OnboardingStep
    completed_steps: List[str]
    is_completed: bool
    started_at: object
    completed_at: Optional[object] = None

    model_config = ConfigDict(from_attributes=True)
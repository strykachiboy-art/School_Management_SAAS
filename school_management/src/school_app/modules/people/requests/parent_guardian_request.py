from typing import Optional
from pydantic import BaseModel, Field, ConfigDict
from school_app.enums.parent_guardian import ParentGuardianEnum

class ParentGuardianCreateRequest(BaseModel):
    user_id: int = Field(..., gt=0, description="The ID of the user record associated with this parent/guardian")
    occupation: str = Field(..., max_length=30, description="The occupation of the parent or guardian")
    relationship: ParentGuardianEnum = Field(..., description="The relationship type (FATHER, MOTHER, GUARDIAN, OTHER)")

    model_config = ConfigDict(from_attributes=True)


class ParentGuardianUpdateRequest(BaseModel):
    occupation: Optional[str] = Field(None, max_length=30, description="The updated occupation")
    relationship: Optional[ParentGuardianEnum] = Field(None, description="The updated relationship type")

    model_config = ConfigDict(from_attributes=True)
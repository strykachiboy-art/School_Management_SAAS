from typing import Optional
from pydantic import BaseModel, Field, ConfigDict
from school_app.enums.parent_guardian import ParentGuardianEnum

class ParentGuardianStudentCreateRequest(BaseModel):
    parent_guardian_id: int = Field(..., gt=0, description="The ID of the parent/guardian record")
    student_id: int = Field(..., gt=0, description="The ID of the student record")
    relationship: ParentGuardianEnum = Field(..., description="The relationship type (FATHER, MOTHER, GUARDIAN, OTHER)")

    model_config = ConfigDict(from_attributes=True)


class ParentGuardianStudentUpdateRequest(BaseModel):
    parent_guardian_id: Optional[int] = Field(None, gt=0, description="The updated ID of the parent/guardian record")
    student_id: Optional[int] = Field(None, gt=0, description="The updated ID of the student record")
    relationship: Optional[ParentGuardianEnum] = Field(None, description="The updated relationship type")

    model_config = ConfigDict(from_attributes=True)
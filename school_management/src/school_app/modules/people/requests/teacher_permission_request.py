from typing import List
from datetime import datetime
from pydantic import BaseModel, ConfigDict, field_validator

from school_app.enums.permission import Permission


class AssignPermissionRequest(BaseModel):
    permission: Permission


class UpdatePermissionsRequest(BaseModel):
    permissions: List[Permission]

    @field_validator("permissions")
    @classmethod
    def no_duplicates(cls, v: List[Permission]) -> List[Permission]:
        if len(v) != len(set(v)):
            raise ValueError("permissions list cannot contain duplicates")
        return v


class TeacherPermissionResponse(BaseModel):
    id: int
    teacher_id: int
    permission: Permission
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True, use_enum_values=True)
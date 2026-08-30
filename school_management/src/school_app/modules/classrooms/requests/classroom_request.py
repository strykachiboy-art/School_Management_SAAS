from datetime import datetime
from typing import Optional, Annotated
from pydantic import BaseModel, ConfigDict, field_validator, conlist, Field


# Base schema containing shared classroom fields
class ClassroomBase(BaseModel):
    name: str
    capacity: int
    location: Optional[str] = None
    teacher_id: Optional[int] = None

    @field_validator("name")
    @classmethod
    def name_not_blank(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("name cannot be blank")
        return v

    @field_validator("capacity")
    @classmethod
    def capacity_positive(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("capacity must be a positive number")
        return v


# Schema used for creating or updating a classroom
class ClassroomCreateRequest(ClassroomBase):
    pass


# Schema used for serializing classroom data in API responses (equivalent to dump_only fields)
class ClassroomResponse(ClassroomBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# Schema used for bulk-assigning students to a classroom
class BulkAssignStudentsRequest(BaseModel):
    student_ids: Annotated[list[int], Field(min_length=1)]

    @field_validator("student_ids")
    @classmethod
    def ids_not_duplicated(cls, v: list[int]) -> list[int]:
        deduped = list(dict.fromkeys(v))
        return deduped
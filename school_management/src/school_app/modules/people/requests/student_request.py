from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field, ConfigDict, field_validator


# Base schema containing shared fields
class StudentBase(BaseModel):
    full_name: str
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    admission_number: Optional[str] = None
    classroom_id: Optional[int] = None
    gender: Optional[str] = None
    date_of_birth: Optional[date] = None
    address: Optional[str] = None

    @field_validator("full_name")
    @classmethod
    def full_name_not_blank(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("full_name cannot be blank")
        return v

    @field_validator("phone")
    @classmethod
    def phone_digits_only(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        v = v.strip()
        if not v.isdigit():
            raise ValueError("phone must contain digits only")
        return v

    @field_validator("gender")
    @classmethod
    def gender_valid_choice(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        allowed = {"male", "female", "non-binary", "prefer not to say"}
        normalized = v.strip().lower()
        if normalized not in allowed:
            raise ValueError(f"gender must be one of {sorted(allowed)}")
        return normalized

    @field_validator("date_of_birth")
    @classmethod
    def dob_not_in_future(cls, v: Optional[date]) -> Optional[date]:
        if v is None:
            return v
        if v > date.today():
            raise ValueError("date_of_birth cannot be in the future")
        return v


# Schema used for creating a student (username/password are create-only)
class StudentCreateRequest(StudentBase):
    username: str
    password: str

    @field_validator("username")
    @classmethod
    def username_valid(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 3:
            raise ValueError("username must be at least 3 characters")
        if not v.replace("_", "").isalnum():
            raise ValueError("username may only contain letters, numbers, and underscores")
        return v

    @field_validator("password")
    @classmethod
    def password_strong_enough(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("password must be at least 8 characters")
        return v


# Schema used for serializing student data in API responses (equivalent to dump_only fields)
class StudentResponse(StudentBase):
    id: int
    user_id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
from pydantic import BaseModel, Field, model_validator


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=8, description="New password must be at least 8 characters long")
    confirm_password: str

    @model_validator(mode="after")
    def validate_passwords(self) -> "ChangePasswordRequest":
        # 1. Check if new password matches confirmation
        if self.new_password != self.confirm_password:
            raise ValueError("New password and confirm password do not match")

        # 2. Prevent setting the new password to the current password
        if self.current_password == self.new_password:
            raise ValueError("New password must be different from current password")

        return self
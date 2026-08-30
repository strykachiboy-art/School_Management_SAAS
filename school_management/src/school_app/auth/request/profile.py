from pydantic import BaseModel, EmailStr, ConfigDict

class ProfileUpdateRequest(BaseModel):
    username: str | None = None
    email: EmailStr | None = None
    
    
class ProfileResponse(BaseModel):
    id: int
    username: str
    email: EmailStr
    role: str

    model_config = ConfigDict(from_attributes=True)
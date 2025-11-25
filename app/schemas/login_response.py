from pydantic import BaseModel

from app.schemas.user import UserResponse


class LoginData(BaseModel):
    access_token: str
    refresh_token: str
    user: UserResponse


class LoginResponse(BaseModel):
    message: str = "Login successful"
    data: LoginData

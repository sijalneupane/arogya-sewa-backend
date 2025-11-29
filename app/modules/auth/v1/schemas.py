from pydantic import BaseModel

from app.modules.user.v1.schema import UserResponse


class JwtPayload(BaseModel):
    sub: str
    role: str
    name: str


class LoginData(BaseModel):
    access_token: str
    refresh_token: str
    user: UserResponse


class LoginResponse(BaseModel):
    message: str = "Login successful"
    data: LoginData

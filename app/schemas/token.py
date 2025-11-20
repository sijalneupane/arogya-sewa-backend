from pydantic import BaseModel

from app.schemas.user import UserResponse


class TokenData(BaseModel):
    access_token: str
    refresh_token: str
    user: UserResponse


class Token(BaseModel):
    message: str = "Login successful"
    data: TokenData

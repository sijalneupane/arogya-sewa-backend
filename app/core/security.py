import datetime

import jwt
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPBearer
from passlib.context import CryptContext

from app.core.config import settings
from app.modules.auth.v1.schemas import JwtPayload

oauth2 = HTTPBearer(auto_error=False)
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")


def verify_password(plain: str, hashed: str):
    return pwd_context.verify(plain, hashed)


def create_access_token(data: JwtPayload):
    to_encode = data.model_dump().copy()
    print(f"Token payload before encoding: {to_encode}")
    expire = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(
        days=settings.ACCESS_TOKEN_EXPIRE_DAYS
    )
    to_encode.update({"exp": expire})
    print(f"Token payload after adding expiration: {to_encode}")
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_refresh_token(data: dict):
    to_encode = data.copy()
    expire = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(
        days=settings.REFRESH_TOKEN_EXPIRE_DAYS
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


async def get_current_user(
    request: Request,
    token: str = Depends(oauth2),
) -> JwtPayload:
    auth_header = request.headers.get("authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="No authentication token provided")

    token = auth_header[7:]  # Remove "Bearer " prefix

    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        # print("Decoded JWT payload:", payload)

        # Try to validate the payload, but handle validation errors gracefully
        try:
            # Remove exp field for validation as it's added by JWT library
            validation_payload = {k: v for k, v in payload.items() if k != "exp"}
            validated_payload = JwtPayload.model_validate(validation_payload)
            # print("Successfully validated payload:", validated_payload)
        except Exception as validation_error:
            print(f"Payload validation warning (continuing anyway): {validation_error}")
            # Continue with the raw payload if validation fails

        return JwtPayload.model_validate(payload)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=401, detail="Invalid token, reenter authentication token"
        )

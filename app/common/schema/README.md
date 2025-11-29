
# schemas — API contracts

Purpose
This directory contains Pydantic models (v2) that define request bodies, query params, and response payloads used by the API.

What lives here
- user.py — UserCreate, UserOut, UserUpdate  
- post.py — PostCreate, PostOut  
- token.py — Token schemas (access/refresh)

Schema types
- Create schemas — for POST requests (e.g., UserCreate)  
- Update schemas — for PATCH/PUT requests (e.g., UserUpdate)  
- Response schemas — for API responses (e.g., UserOut)  
- Base schemas — shared common fields / DTOs

Rules / best practices
- Keep schemas focused on API contracts, not business logic.  
- Use Pydantic BaseModel (v2) and proper type hints for all fields.  
- Add validation using Pydantic validators when needed.  
- Do not import SQLAlchemy (or ORM) models here — keep layers separated.  
- For models that are populated from ORM objects, enable attribute loading (Pydantic v2): e.g. set model_config = ConfigDict(from_attributes=True).  
- Exclude sensitive fields (password, hashed_password) from response models.

Examples

schemas/user.py
```python
from pydantic import BaseModel, ConfigDict, EmailStr

class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str

class UserOut(BaseModel):
    id: int
    username: str
    email: EmailStr
    model_config = ConfigDict(from_attributes=True)  # allow conversion from ORM-like objects
```

Usage (FastAPI)
```python
from fastapi import FastAPI
from schemas.user import UserCreate, UserOut

app = FastAPI()

@app.post("/users/", response_model=UserOut)
def create_user(user: UserCreate):
    # user is validated; business logic creates user and returns an ORM object
    pass
```

Keep README updated with any new schema files and validation patterns used across the project.

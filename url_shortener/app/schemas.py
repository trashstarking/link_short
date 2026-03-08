from pydantic import BaseModel, AnyUrl
from datetime import datetime
from typing import Optional

# auth schemas
class UserCreate(BaseModel):
    username: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

# link schemas
class LinkBase(BaseModel):
    original_url: AnyUrl
    custom_alias: Optional[str] = None
    expires_at: Optional[datetime] = None

class LinkCreate(LinkBase):
    pass

class LinkUpdate(BaseModel):
    original_url: AnyUrl

class LinkResponse(BaseModel):
    short_code: str
    original_url: AnyUrl
    created_at: datetime
    expires_at: Optional[datetime]
    click_count: int
    is_active: bool

    class Config:
        from_attributes = True

class LinkStats(LinkResponse):
    last_accessed_at: Optional[datetime]
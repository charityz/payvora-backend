from pydantic import BaseModel
from typing import Optional


class MerchantRegister(BaseModel):
    name: str
    email: str
    password: str
    business_name: str
    logo_url: Optional[str]

class MerchantLogin(BaseModel):
    email: str
    password: str
    


class UpdateProfileRequest(BaseModel):
    business_name: Optional[str] = None
    logo_url: Optional[str] = None
    name: Optional[str] = None


class UpdatePasswordRequest(BaseModel):
    current_password: str
    new_password: str


class WebhookRequest(BaseModel):
    webhook_url: str
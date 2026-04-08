from pydantic import BaseModel, EmailStr
from typing import Optional
from enum import Enum


class PaymentMethod(str, Enum):
    card = "card"
    bank_transfer = "bank_transfer"
    ussd = "ussd"
    wallet = "wallet"


class TransactionRequest(BaseModel):
    # merchant_id: Optional[str]
    amount: float
    payment_method: PaymentMethod
    customer_name: Optional[str] = "Anonymous"
    customer_email: Optional[EmailStr] = None
    purpose: str = ""
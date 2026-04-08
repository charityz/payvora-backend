from fastapi import APIRouter, HTTPException
from app.schemas.merchant_model import MerchantRegister, MerchantLogin
import uuid
from app.database.db import merchant_collection
from app.utils.services import hash_password, verify_password
from app.utils.generate_key import generate_secret_key, generate_public_key
import jwt
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, Depends
from app.utils.security import get_current_merchant
from app.database.db import merchant_collection
from app.schemas.merchant_model import UpdateProfileRequest, WebhookRequest, UpdatePasswordRequest



SECRET_KEY = "your_secret_key"
router = APIRouter()

@router.post("/register")
def register_merchant(data: MerchantRegister):

    existing = merchant_collection.find_one({"email": data.email})

    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    merchant_id = str(uuid.uuid4())

    merchant = {
        "merchant_id": merchant_id,
        "name": data.name,
        "email": data.email,
        "password": hash_password(data.password),
        "business_name": data.business_name,
        "logo_url": data.logo_url,
        "public_key": generate_public_key(),
        "secret_key": generate_secret_key(),
        "created_at": datetime.now()
    }

    merchant_collection.insert_one(merchant)

    return {
        "message": "Merchant registered successfully",
        "public_key": merchant["public_key"],
        "secret_key": merchant["secret_key"]
    }



@router.post("/login")
def login(data: MerchantLogin):

    user = merchant_collection.find_one({"email": data.email})

    if not user or not verify_password(data.password, user["password"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    payload = {
        "merchant_id": user["merchant_id"],
        "email": user["email"],
        "name": user["name"],
        "business_name": user["business_name"],
        "public_key": user["public_key"],  
        "secret_key": user["secret_key"],
        "exp": datetime.utcnow() + timedelta(hours=2)
    }

    token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")

    return {
        "access_token": token,
        "merchant_id": user["merchant_id"],
        "name": user["name"],
        "business_name": user["business_name"]
    }


# ── UPDATE PROFILE ──
@router.put("/profile/update")
def update_profile(data: UpdateProfileRequest, merchant: dict = Depends(get_current_merchant)):
    updates = {k: v for k, v in data.dict().items() if v is not None}
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    merchant_collection.update_one(
        {"merchant_id": merchant["merchant_id"]},
        {"$set": updates}
    )
    return {"message": "Profile updated successfully", **updates}


# ── UPDATE PASSWORD ──
@router.put("/profile/password")
def update_password(data: UpdatePasswordRequest, merchant: dict = Depends(get_current_merchant)):
    if not verify_password(data.current_password, merchant["password"]):
        raise HTTPException(status_code=401, detail="Current password is incorrect")
    if len(data.new_password) < 8:
        raise HTTPException(status_code=400, detail="New password must be at least 8 characters")
    merchant_collection.update_one(
        {"merchant_id": merchant["merchant_id"]},
        {"$set": {"password": hash_password(data.new_password)}}
    )
    return {"message": "Password updated successfully"}


# ── SAVE WEBHOOK URL ──
@router.put("/webhook/update")
def update_webhook(data: WebhookRequest, merchant: dict = Depends(get_current_merchant)):
    merchant_collection.update_one(
        {"merchant_id": merchant["merchant_id"]},
        {"$set": {"webhook_url": data.webhook_url}}
    )
    return {"message": "Webhook URL saved successfully"}


# ── GET WEBHOOK URL ──
@router.get("/webhook")
def get_webhook(merchant: dict = Depends(get_current_merchant)):
    return {"webhook_url": merchant.get("webhook_url", "")}





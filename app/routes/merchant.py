from fastapi import APIRouter, HTTPException, Depends
from app.schemas.merchant_model import MerchantRegister, MerchantLogin, UpdateProfileRequest, WebhookRequest, UpdatePasswordRequest
import uuid
from app.database.db import merchant_collection
from app.utils.services import hash_password, verify_password
from app.utils.generate_key import generate_secret_key, generate_public_key
import jwt
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta, timezone
from app.utils.security import get_current_merchant

load_dotenv()
SECRET_KEY = os.getenv("SECRET_KEY")
router = APIRouter()


@router.post("/register")
def register_merchant(data: MerchantRegister):
    try:
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
            "category": data.category,
            "logo_url": str(data.logo_url) if data.logo_url else None,
            "public_key": generate_public_key(),
            "secret_key": generate_secret_key(),
            "created_at": datetime.now(timezone.utc),
        }
        merchant_collection.insert_one(merchant)

        return {
            "message": "Merchant registered successfully",
            "public_key": merchant["public_key"],
            "secret_key": merchant["secret_key"],
        }
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=500, detail="Registration failed. Please try again.")


@router.post("/login")
def login(data: MerchantLogin):
    try:
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
            "exp": datetime.now(timezone.utc) + timedelta(hours=2),
        }
        token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")

        return {
            "access_token": token,
            "merchant_id": user["merchant_id"],
            "name": user["name"],
            "business_name": user["business_name"],
        }
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=500, detail="Login failed. Please try again.")


# ── UPDATE PROFILE ──
@router.put("/profile/update")
def update_profile(data: UpdateProfileRequest, merchant: dict = Depends(get_current_merchant)):
    try:
        updates = {k: v for k, v in data.dict().items() if v is not None}
        if not updates:
            raise HTTPException(status_code=400, detail="No fields to update")
        merchant_collection.update_one(
            {"merchant_id": merchant["merchant_id"]},
            {"$set": updates},
        )
        return {"message": "Profile updated successfully", **updates}
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to update profile.")


# ── UPDATE PASSWORD ──
@router.put("/profile/password")
def update_password(data: UpdatePasswordRequest, merchant: dict = Depends(get_current_merchant)):
    try:
        if not verify_password(data.current_password, merchant["password"]):
            raise HTTPException(status_code=401, detail="Current password is incorrect")
        if len(data.new_password) < 8:
            raise HTTPException(status_code=400, detail="New password must be at least 8 characters")
        merchant_collection.update_one(
            {"merchant_id": merchant["merchant_id"]},
            {"$set": {"password": hash_password(data.new_password)}},
        )
        return {"message": "Password updated successfully"}
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to update password.")


# ── SAVE WEBHOOK URL ──
@router.put("/webhook/update")
def update_webhook(data: WebhookRequest, merchant: dict = Depends(get_current_merchant)):
    try:
        merchant_collection.update_one(
            {"merchant_id": merchant["merchant_id"]},
            {"$set": {"webhook_url": data.webhook_url}},
        )
        return {"message": "Webhook URL saved successfully"}
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to save webhook URL.")


# ── GET WEBHOOK URL ──
@router.get("/webhook")
def get_webhook(merchant: dict = Depends(get_current_merchant)):
    try:
        return {"webhook_url": merchant.get("webhook_url", "")}
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to retrieve webhook URL.")


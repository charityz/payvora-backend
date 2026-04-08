from fastapi import Security, HTTPException
from fastapi.security.api_key import APIKeyHeader
from app.database.db import merchant_collection
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
from app.database.db import merchant_collection

SECRET_KEY = "your_secret_key"
bearer_scheme = HTTPBearer()

api_key_header = APIKeyHeader(name="Authorization", auto_error=False)


def get_api_key(api_key: str = Security(api_key_header)):

    if not api_key:
        raise HTTPException(status_code=401, detail="API key missing")

    merchant = merchant_collection.find_one({"secret_key": api_key})

    if not merchant:
        raise HTTPException(status_code=401, detail="Invalid API key")

    return merchant



def get_current_merchant(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        email = payload.get("email")
        if not email:
            raise HTTPException(status_code=401, detail="Invalid token")
        merchant = merchant_collection.find_one({"email": email}, {"_id": 0})
        if not merchant:
            raise HTTPException(status_code=404, detail="Merchant not found")
        return merchant
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")
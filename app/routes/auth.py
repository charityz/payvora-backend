from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse
from app.database.db import merchant_collection
import jwt
import os
from dotenv import load_dotenv
from fastapi.templating import Jinja2Templates

load_dotenv()
SECRET_KEY = os.getenv("SECRET_KEY")

templates = Jinja2Templates(directory="templates")
router = APIRouter()

def verify_token(request: Request):
    token = request.headers.get("Authorization")

    if not token:
        raise HTTPException(status_code=401, detail="Unauthorized")

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Invalid token")
    



@router.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request})


@router.get("/api/merchant")
def get_merchant(request: Request):
    payload = verify_token(request)

    merchant = merchant_collection.find_one({"email": payload["email"]})

    return {
        "name": merchant["name"],
        "email": merchant["email"]
    }

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi import HTTPException
from app.schemas.transaction_model import TransactionRequest
from app.database.db import transaction_collection
from app.utils.generate_reference import generate_reference
from app.utils.security import get_api_key
from fastapi.templating import Jinja2Templates
from app.utils.security import get_current_merchant
from app.utils.email import send_receipt_email
from datetime import datetime
from fastapi.responses import StreamingResponse
from app.utils.receipt_pdf import generate_receipt_pdf
import io
from app.utils.fraud_detector import calculate_fraud_score
import httpx
from app.database.db import merchant_collection


templates = Jinja2Templates(directory="app/templates")
router = APIRouter()

# INITIALIZE PAYMENT

@router.post("/initialize_payment")
def initialize_payment(
    data: TransactionRequest,
    merchant: dict = Depends(get_api_key)
):
    reference = generate_reference()

    # ── RUN FRAUD SCORING ──
    fraud_result = calculate_fraud_score(
        merchant_id=merchant["merchant_id"],
        customer_email=data.customer_email or "",
        amount=data.amount,
        payment_method=data.payment_method.value,
    )

    transaction = {
        "reference": reference,
        "merchant_id": merchant["merchant_id"],
        "email": data.customer_email,
        "customer_name": data.customer_name,
        "amount": data.amount,
        "purpose": data.purpose,
        "business_name": merchant["business_name"],
        "logo_url": merchant.get("logo_url"),
        "payment_method": data.payment_method.value,
        "status": fraud_result["recommended_status"],  # auto-flag if high risk
        "fraud_score": fraud_result["fraud_score"],
        "risk_level": fraud_result["risk_level"],
        "fraud_reasons": fraud_result["fraud_reasons"],
        "signals": fraud_result["signals"],
        "created_at": datetime.utcnow(),
        "completed_at": None,
    }

    transaction_collection.insert_one(transaction)

    payment_link = f"http://localhost:8000/api/v1/pay/{reference}"

    return {
        "message": "Payment initialized successfully",
        "reference": reference,
        "payment_link": payment_link,
        "fraud_score": fraud_result["fraud_score"],
        "risk_level": fraud_result["risk_level"],
    }




# PAY REFERENCE
@router.get("/pay/{reference}")
def payment_page(request: Request, reference: str):

    transaction = transaction_collection.find_one({"reference": reference})

    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")

    return templates.TemplateResponse("checkout.html", {
        "request": request,
        "reference": reference,
        "amount": transaction["amount"],
        "email": transaction.get("email"),
        "business": transaction.get("business_name"),
        "logo": transaction.get("logo_url")
    })



    
# PAYMENT COMPLETION      
# @router.post("/payment/complete/{reference}")
# async def complete_payment(reference: str):
#     transaction = transaction_collection.find_one({"reference": reference})

#     if not transaction:
#         raise HTTPException(status_code=404, detail="Transaction not found")

#     if transaction["status"] == "success":
#         raise HTTPException(status_code=400, detail="Payment already completed")

#     completed_at = datetime.utcnow()

#     transaction_collection.update_one(
#         {"reference": reference},
#         {"$set": {"status": "success", "completed_at": completed_at}}
#     )
#     print(f"✅ Payment complete for {reference}")           # ← add this
#     print(f"📧 Sending email to: {transaction.get('email')}")  # ← add this


#     try:
#         await send_receipt_email(
#             customer_email=transaction.get("email", ""),
#             customer_name=transaction.get("email", "").split("@")[0],
#             business_name=transaction.get("business_name", ""),
#             logo_url=transaction.get("logo_url", ""),   # ← from transaction
#             amount=float(transaction.get("amount", 0)),
#             purpose=transaction.get("purpose", ""),
#             reference=reference,
#             payment_method=transaction.get("payment_method", "card"),
#             date=completed_at.strftime("%d %B %Y, %I:%M %p"),
#         )
#     except Exception as e:
#         print(f"Email error: {e}")

#     return {"message": "Payment successful", "receipt_sent": True}
    
    

@router.post("/payment/complete/{reference}")
async def complete_payment(reference: str):
    transaction = transaction_collection.find_one({"reference": reference})
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    if transaction["status"] == "success":
        raise HTTPException(status_code=400, detail="Payment already completed")

    completed_at = datetime.utcnow()
    transaction_collection.update_one(
        {"reference": reference},
        {"$set": {"status": "success", "completed_at": completed_at}}
    )

    # Send receipt email
    try:
        await send_receipt_email(
            customer_email=transaction.get("email", ""),
            customer_name=transaction.get("customer_name", ""),
            business_name=transaction.get("business_name", ""),
            logo_url=transaction.get("logo_url", ""),
            amount=float(transaction.get("amount", 0)),
            reference=reference,
            payment_method=transaction.get("payment_method", "card"),
            date=completed_at.strftime("%d %B %Y, %I:%M %p"),
            purpose=transaction.get("purpose", ""),
        )
    except Exception as e:
        print(f"Email error: {e}")

    # ── FIRE WEBHOOK ──
    try:
        merchant = merchant_collection.find_one(
            {"merchant_id": transaction["merchant_id"]}, {"_id": 0}
        )
        webhook_url = merchant.get("webhook_url", "") if merchant else ""
        if webhook_url:
            payload = {
                "event": "payment.success",
                "reference": reference,
                "amount": float(transaction.get("amount", 0)),
                "customer_email": transaction.get("email", ""),
                "customer_name": transaction.get("customer_name", ""),
                "purpose": transaction.get("purpose", ""),
                "payment_method": transaction.get("payment_method", ""),
                "business_name": transaction.get("business_name", ""),
                "completed_at": completed_at.strftime("%Y-%m-%d %H:%M:%S"),
            }
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(webhook_url, json=payload)
                print(f"✅ Webhook fired to {webhook_url} — status {resp.status_code}")
    except Exception as e:
        print(f"Webhook error: {e}")

    return {"message": "Payment successful", "receipt_sent": True}



# VERIFY PAYMENT
@router.get("/payments/verify/{reference}")
def verify_payment(reference: str):

    transaction = transaction_collection.find_one({"reference": reference})

    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")

    return {
        "reference": reference,
        "status": transaction["status"],
        "amount": transaction["amount"],
        "email": transaction.get("email"),
    }


# TRANSACTION ROUTE
@router.get("/transactions")
def get_transactions(merchant: dict = Depends(get_api_key)):
    txns = list(transaction_collection.find(
        {"merchant_id": merchant["merchant_id"]},
        {"_id": 0}
    ))
    for t in txns:
        if t.get("created_at"):
            t["created_at"] = t["created_at"].strftime("%Y-%m-%d %H:%M:%S")
        if t.get("completed_at"):
            t["completed_at"] = t["completed_at"].strftime("%Y-%m-%d %H:%M:%S")
            
        t.setdefault("fraud_score", 0)
        t.setdefault("risk_level", "low")
        t.setdefault("fraud_reasons", [])
    return {"transactions": txns}



# DOWNLOAD RECEIPTS
@router.get("/receipt/download/{reference}")
def download_receipt(reference: str, merchant: dict = Depends(get_api_key)):
    transaction = transaction_collection.find_one(
        {"reference": reference, "merchant_id": merchant["merchant_id"]},
        {"_id": 0}
    )

    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")

    if transaction["status"] != "success":
        raise HTTPException(status_code=400, detail="Receipt only available for successful payments")

    completed_at = transaction.get("completed_at", transaction.get("created_at", ""))
    date_str = completed_at.strftime("%d %B %Y, %I:%M %p") if hasattr(completed_at, "strftime") else str(completed_at)

    pdf_bytes = generate_receipt_pdf(
        reference=reference,
        business_name=transaction.get("business_name", ""),
        logo_url=transaction.get("logo_url", ""),
        customer_email=transaction.get("email", ""),
        amount=float(transaction.get("amount", 0)),
        purpose=transaction.get("purpose", ""), 
        payment_method=transaction.get("payment_method", "card"),
        date=date_str,
    )

    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=receipt_{reference}.pdf"}
    )
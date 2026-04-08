from fastapi_mail import FastMail, MessageSchema, ConnectionConfig, MessageType
from fastapi_mail.schemas import MultipartSubtypeEnum
from app.utils.receipt_pdf import generate_receipt_pdf
import base64
import tempfile
import os
from dotenv import load_dotenv

load_dotenv()

conf = ConnectionConfig(
    MAIL_USERNAME=os.getenv("MAIL_USERNAME"),
    MAIL_PASSWORD=os.getenv("MAIL_PASSWORD"),
    MAIL_FROM="noreply.payvora@gmail.com",
    MAIL_FROM_NAME="Payvora",
    MAIL_PORT=587,
    MAIL_SERVER="smtp.gmail.com",
    MAIL_STARTTLS=True,
    MAIL_SSL_TLS=False,
    USE_CREDENTIALS=True,
)

async def send_receipt_email(
    customer_email: str,
    customer_name: str,
    business_name: str,
    logo_url: str,
    amount: float,
    reference: str,
    payment_method: str,
    date: str,
    purpose: str = "",
):
    # ── GENERATE PDF AND SAVE TO TEMP FILE ──
    pdf_bytes = generate_receipt_pdf(
        reference=reference,
        business_name=business_name,
        logo_url=logo_url,
        customer_email=customer_email,
        amount=amount,
        payment_method=payment_method,
        date=date,
        purpose=purpose,
    )

    # Save PDF to a temporary file
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(
            delete=False,
            suffix=".pdf",
            prefix=f"receipt_{reference}_"
        ) as tmp:
            tmp.write(pdf_bytes)
            tmp_path = tmp.name

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head><meta charset="UTF-8"/>
        <style>
          body {{ font-family: Arial, sans-serif; background: #f3f4f6; margin: 0; padding: 2rem; }}
          .container {{ max-width: 520px; margin: 0 auto; background: #fff; border-radius: 16px; overflow: hidden; box-shadow: 0 4px 24px rgba(0,0,0,0.08); }}
          .header {{ background: linear-gradient(135deg, #6366f1, #8b5cf6); padding: 2rem; text-align: center; }}
          .logo {{ width: 64px; height: 64px; border-radius: 50%; object-fit: cover; margin: 0 auto 1rem; display: block; border: 3px solid rgba(255,255,255,0.3); }}
          .logo-placeholder {{ width: 64px; height: 64px; border-radius: 50%; background: rgba(255,255,255,0.2); margin: 0 auto 1rem; display: flex; align-items: center; justify-content: center; font-size: 1.5rem; color: #fff; font-weight: 700; }}
          .biz-name {{ color: #fff; font-size: 1.2rem; font-weight: 700; margin: 0 0 .3rem; }}
          .receipt-label {{ color: rgba(255,255,255,0.75); font-size: .88rem; margin: 0; }}
          .body {{ padding: 2rem; }}
          .amount-box {{ background: #f0fdf4; border: 1.5px solid #86efac; border-radius: 12px; padding: 1.2rem; text-align: center; margin-bottom: 1.5rem; }}
          .amount-label {{ font-size: .78rem; color: #16a34a; text-transform: uppercase; letter-spacing: .5px; margin-bottom: .3rem; }}
          .amount-value {{ font-size: 2rem; font-weight: 700; color: #14532d; }}
          .detail-row {{ display: flex; justify-content: space-between; align-items: center; padding: .7rem 0; border-bottom: 1px solid #f3f4f6; font-size: .88rem; }}
          .detail-row:last-child {{ border-bottom: none; }}
          .detail-key {{ color: #6b7280; }}
          .detail-val {{ font-weight: 600; color: #111827; font-family: monospace; }}
          .footer {{ background: #f9fafb; padding: 1.2rem 2rem; text-align: center; font-size: .78rem; color: #9ca3af; border-top: 1px solid #f3f4f6; }}
          .brand {{ font-weight: 700; color: #6366f1; }}
        </style>
        </head>
        <body>
          <div class="container">
            <div class="header">
              {'<img src="' + logo_url + '" class="logo" alt="logo"/>' if logo_url else '<div class="logo-placeholder">' + (business_name[0].upper() if business_name else "P") + '</div>'}
              <h1 class="biz-name">{business_name}</h1>
              <p class="receipt-label">Payment Receipt</p>
            </div>
            <div class="body">
              <p style="color:#374151;margin-bottom:1.5rem;font-size:.95rem;">
                Hi <strong>{customer_name or customer_email}</strong>, your payment to
                <strong>{business_name}</strong> was successful.
                Your PDF receipt is attached to this email.
              </p>
              <div class="amount-box">
                <div class="amount-label">Amount Paid</div>
                <div class="amount-value">&#8358;{amount:,.0f}</div>
              </div>
              <div class="detail-row"><span class="detail-key">Reference</span><span class="detail-val">{reference}</span></div>
              <div class="detail-row"><span class="detail-key">Purpose</span><span class="detail-val">{purpose or "—"}</span></div>
              <div class="detail-row"><span class="detail-key">Business</span><span class="detail-val">{business_name}</span></div>
              <div class="detail-row"><span class="detail-key">Payment Method</span><span class="detail-val">{payment_method.title()}</span></div>
              <div class="detail-row"><span class="detail-key">Date</span><span class="detail-val">{date}</span></div>
              <div class="detail-row"><span class="detail-key">Status</span><span class="detail-val" style="color:#16a34a;">&#10003; Successful</span></div>
            </div>
            <div class="footer">
              Powered by <span class="brand">Payvora</span> &nbsp;·&nbsp; Secure Payment Infrastructure<br/>
              PDF receipt is attached to this email.
            </div>
          </div>
        </body>
        </html>
        """

        message = MessageSchema(
            subject=f"Payment Receipt — ₦{amount:,.0f} | {business_name}",
            recipients=[customer_email],
            body=html_content,
            subtype=MessageType.html,
            attachments=[tmp_path],  # ← pass file path directly
        )

        fm = FastMail(conf)
        await fm.send_message(message)
        print(f"✅ Email sent to {customer_email}")

    finally:
        # ── CLEAN UP TEMP FILE ──
        if tmp_path and os.path.exists(tmp_path):
            os.remove(tmp_path)
            print(f"🗑 Temp file cleaned up: {tmp_path}")
from datetime import datetime, timedelta
from app.database.db import transaction_collection


# ── THRESHOLDS ──
HIGH_AMOUNT_THRESHOLD = 500_000      # ₦500,000
MEDIUM_AMOUNT_THRESHOLD = 150_000    # ₦150,000
VELOCITY_WINDOW_MINUTES = 10         # time window to check velocity
VELOCITY_MAX_TRANSACTIONS = 3        # max transactions allowed in window
LATE_NIGHT_START = 0                 # 12am
LATE_NIGHT_END = 5                   # 5am
FAILED_ATTEMPTS_THRESHOLD = 3        # max failed attempts before flagging


def calculate_fraud_score(
    merchant_id: str,
    customer_email: str,
    amount: float,
    payment_method: str,
) -> dict:
    """
    Calculates a fraud score (0-100) for a transaction.
    Returns score, risk level, and reasons.
    """
    score = 0
    reasons = []
    signals = {}

    now = datetime.utcnow()

    # ── SIGNAL 1: LARGE AMOUNT ──
    if amount >= HIGH_AMOUNT_THRESHOLD:
        score += 35
        reasons.append(f"Very large transaction amount (₦{amount:,.0f})")
        signals["large_amount"] = True
    elif amount >= MEDIUM_AMOUNT_THRESHOLD:
        score += 15
        reasons.append(f"Above average transaction amount (₦{amount:,.0f})")
        signals["large_amount"] = False

    # ── SIGNAL 2: TIME OF DAY (late night) ──
    hour = now.hour
    if LATE_NIGHT_START <= hour < LATE_NIGHT_END:
        score += 20
        reasons.append(f"Transaction initiated at unusual hour ({hour:02d}:00 WAT)")
        signals["late_night"] = True
    else:
        signals["late_night"] = False

    # ── SIGNAL 3: TRANSACTION VELOCITY ──
    # Count how many transactions from same email in last N minutes
    window_start = now - timedelta(minutes=VELOCITY_WINDOW_MINUTES)
    recent_count = transaction_collection.count_documents({
        "email": customer_email,
        "created_at": {"$gte": window_start},
    }) if customer_email else 0

    if recent_count >= VELOCITY_MAX_TRANSACTIONS:
        score += 30
        reasons.append(f"High transaction velocity — {recent_count} transactions in {VELOCITY_WINDOW_MINUTES} mins")
        signals["high_velocity"] = True
    elif recent_count >= 2:
        score += 10
        reasons.append(f"Multiple transactions in short period ({recent_count} in {VELOCITY_WINDOW_MINUTES} mins)")
        signals["high_velocity"] = False
    else:
        signals["high_velocity"] = False

    # ── SIGNAL 4: REPEATED FAILED ATTEMPTS ──
    failed_count = transaction_collection.count_documents({
        "email": customer_email,
        "status": "failed",
        "created_at": {"$gte": now - timedelta(hours=1)},
    }) if customer_email else 0

    if failed_count >= FAILED_ATTEMPTS_THRESHOLD:
        score += 25
        reasons.append(f"Repeated failed attempts — {failed_count} failed in last hour")
        signals["repeated_failures"] = True
    elif failed_count > 0:
        score += 8
        reasons.append(f"Previous failed attempt detected ({failed_count} in last hour)")
        signals["repeated_failures"] = False
    else:
        signals["repeated_failures"] = False

    # ── SIGNAL 5: PAYMENT METHOD RISK ──
    method_scores = {
        "card": 10,          # cards have higher fraud risk
        "bank_transfer": 0,  # transfers are generally safer
        "ussd": 5,
        "wallet": 3,
    }
    method_score = method_scores.get(payment_method, 5)
    if method_score > 0:
        score += method_score
        if payment_method == "card":
            reasons.append("Card payment — slightly higher fraud risk")
        signals["risky_method"] = payment_method == "card"
    else:
        signals["risky_method"] = False

    # ── CAP SCORE AT 100 ──
    score = min(score, 100)

    # ── DETERMINE RISK LEVEL ──
    if score >= 70:
        risk_level = "high"
        status = "flagged"
    elif score >= 40:
        risk_level = "medium"
        status = "pending"
    else:
        risk_level = "low"
        status = "pending"

    return {
        "fraud_score": score,
        "risk_level": risk_level,
        "fraud_reasons": reasons,
        "signals": signals,
        "recommended_status": status,
        "checked_at": now.strftime("%Y-%m-%d %H:%M:%S"),
    }
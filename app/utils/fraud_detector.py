from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from app.database.db import transaction_collection, merchant_collection
from app.ml.fraud_ml import scorer as ml_scorer


# ── THRESHOLDS ──
EXTREME_AMOUNT_THRESHOLD = 50_000_000    # ₦50,000,000
HIGH_AMOUNT_THRESHOLD = 10_000_000         # ₦10,000,000
MEDIUM_AMOUNT_THRESHOLD = 2_000_000       # ₦2,000,000
VELOCITY_WINDOW_MINUTES = 10
VELOCITY_MAX_TRANSACTIONS = 3
LATE_NIGHT_START = 0
LATE_NIGHT_END = 5
FAILED_ATTEMPTS_THRESHOLD = 3

MERCHANT_RISK_SCORES = {
    # High risk
    "crypto":          30,
    "gambling":        25,
    "gift_cards":      20,
    "forex":           20,
    "finance":         18,  # money laundering, account takeover exposure
    # Medium risk
    "gaming":          10,
    "logistics":        8,  # cash-on-delivery fraud, package interception
    "other":            8,  # unknown category is itself a mild signal
    "entertainment":    5,
    "ecommerce":        5,
    "technology":       5,
    "retail":           5,
    # Low risk
    "health_wellness":  2,
    "food_beverage":    0,
    "utilities":        0,
    "education":        0,
}

METHOD_SCORES = {
    "card":          10,
    "bank_transfer":  0,
    "ussd":           5,
    "wallet":         3,
}

DANGEROUS_COMBOS = [
    ({"late_night", "large_amount", "risky_method"}, 25, "Late night + large card payment"),
    ({"high_velocity", "repeated_failures"},          20, "Velocity spike with prior failures"),
    ({"risky_merchant", "large_amount"},              15, "Large amount at high-risk merchant"),
    ({"late_night", "high_velocity"},                 15, "Late night velocity spike"),
]


class FraudDetector:
    def __init__(
        self,
        merchant_id: str,
        customer_email: str,
        amount: float,
        payment_method: str,
        ip_address: str | None = None,
        device_fingerprint: str | None = None,
    ):
        self.merchant_id = merchant_id
        self.customer_email = customer_email
        self.amount = amount
        self.payment_method = payment_method
        self.ip_address = ip_address
        self.device_fingerprint = device_fingerprint

        self.score = 0
        self.reasons = []
        self.signals = {}
        self.now = datetime.now(timezone.utc)

    # ── SIGNAL 1: LARGE AMOUNT ──
    def _check_amount(self):
        if self.amount >= EXTREME_AMOUNT_THRESHOLD:
            self.score += 55
            self.reasons.append(f"Extreme transaction amount (₦{self.amount:,.0f})")
            self.signals["large_amount"] = True
        elif self.amount >= HIGH_AMOUNT_THRESHOLD:
            self.score += 35
            self.reasons.append(f"Very large transaction amount (₦{self.amount:,.0f})")
            self.signals["large_amount"] = True
        elif self.amount >= MEDIUM_AMOUNT_THRESHOLD:
            self.score += 15
            self.reasons.append(f"Above average transaction amount (₦{self.amount:,.0f})")
            self.signals["large_amount"] = False
        else:
            self.signals["large_amount"] = False

    # ── SIGNAL 2: TIME OF DAY (late night WAT) ──
    def _check_time_of_day(self):
        hour = self.now.astimezone(ZoneInfo("Africa/Lagos")).hour
        if LATE_NIGHT_START <= hour < LATE_NIGHT_END:
            self.score += 20
            self.reasons.append(f"Transaction initiated at unusual hour ({hour:02d}:00 WAT)")
            self.signals["late_night"] = True
        else:
            self.signals["late_night"] = False

    # ── SIGNAL 3: TRANSACTION VELOCITY ──
    def _count_recent(self, field: str, value: str | None) -> int:
        if not value:
            return 0
        window_start = self.now - timedelta(minutes=VELOCITY_WINDOW_MINUTES)
        return transaction_collection.count_documents({
            field: value,
            "created_at": {"$gte": window_start},
        })

    def _check_velocity(self):
        recent_count = max(
            self._count_recent("email", self.customer_email),
            self._count_recent("ip_address", self.ip_address),
            self._count_recent("device_fingerprint", self.device_fingerprint),
        )
        if recent_count >= VELOCITY_MAX_TRANSACTIONS:
            self.score += 30
            self.reasons.append(f"High velocity — {recent_count} transactions in {VELOCITY_WINDOW_MINUTES} mins")
            self.signals["high_velocity"] = True
        elif recent_count >= 2:
            self.score += 10
            self.reasons.append(f"Multiple recent transactions ({recent_count} in {VELOCITY_WINDOW_MINUTES} mins)")
            self.signals["high_velocity"] = False
        else:
            self.signals["high_velocity"] = False

    # ── SIGNAL 4: REPEATED FAILED ATTEMPTS ──
    def _check_failed_attempts(self):
        failed_count = transaction_collection.count_documents({
            "email": self.customer_email,
            "status": "failed",
            "created_at": {"$gte": self.now - timedelta(hours=1)},
        }) if self.customer_email else 0

        if failed_count >= FAILED_ATTEMPTS_THRESHOLD:
            self.score += 25
            self.reasons.append(f"Repeated failed attempts — {failed_count} failed in last hour")
            self.signals["repeated_failures"] = True
        elif failed_count > 0:
            self.score += 8
            self.reasons.append(f"Previous failed attempt detected ({failed_count} in last hour)")
            self.signals["repeated_failures"] = False
        else:
            self.signals["repeated_failures"] = False

    # ── SIGNAL 5: PAYMENT METHOD RISK ──
    def _check_payment_method(self):
        method_score = METHOD_SCORES.get(self.payment_method, 5)
        if method_score > 0:
            self.score += method_score
            if self.payment_method == "card":
                self.reasons.append("Card payment — slightly higher fraud risk")
            self.signals["risky_method"] = self.payment_method == "card"
        else:
            self.signals["risky_method"] = False

    # ── SIGNAL 6: MERCHANT CATEGORY RISK ──
    def _check_merchant_risk(self):
        merchant = merchant_collection.find_one({"merchant_id": self.merchant_id})
        category = merchant.get("category", "unknown") if merchant else "unknown"
        merchant_score = MERCHANT_RISK_SCORES.get(category, 8)  # unrecognised category treated as "other"

        if merchant_score > 0:
            self.score += merchant_score
            self.reasons.append(f"Merchant category '{category}' has inherent risk")
            self.signals["risky_merchant"] = True
        else:
            self.signals["risky_merchant"] = False

    # ── SIGNAL 7: ML MODEL SCORE ──
    def _check_ml_score(self):
        if ml_scorer is None:
            return   # model not trained yet — skip silently

        hour = self.now.astimezone(ZoneInfo("Africa/Lagos")).hour
        ml_prob = ml_scorer.predict(
            amount=self.amount,
            payment_method=self.payment_method,
            hour=hour,
        )
        self.signals["ml_fraud_probability"] = round(ml_prob, 4)

        if ml_prob >= 0.7:
            self.score += 25
            self.reasons.append(f"ML model flagged high fraud probability ({ml_prob:.0%})")
        elif ml_prob >= 0.4:
            self.score += 10
            self.reasons.append(f"ML model detected elevated fraud risk ({ml_prob:.0%})")

    # ── CORRELATION BONUSES ──
    def _check_combinations(self):
        active = {k for k, v in self.signals.items() if v}
        for combo, bonus, label in DANGEROUS_COMBOS:
            if combo.issubset(active):
                self.score += bonus
                self.reasons.append(f"Suspicious combination: {label}")

    # ── DETERMINE RISK LEVEL ──
    def _resolve_risk(self) -> tuple[str, str]:
        if self.score >= 70:
            return "high", "flagged"
        elif self.score >= 40:
            return "medium", "pending"
        return "low", "pending"

    def calculate(self) -> dict:
        self._check_amount()
        self._check_time_of_day()
        self._check_velocity()
        self._check_failed_attempts()
        self._check_payment_method()
        self._check_merchant_risk()
        self._check_ml_score()
        self._check_combinations()

        self.score = min(self.score, 100)
        risk_level, status = self._resolve_risk()

        return {
            "fraud_score": self.score,
            "risk_level": risk_level,
            "fraud_reasons": self.reasons,
            "signals": self.signals,
            "recommended_status": status,
            "checked_at": self.now.astimezone(ZoneInfo("Africa/Lagos")).isoformat(),
        }


def calculate_fraud_score(
    merchant_id: str,
    customer_email: str,
    amount: float,
    payment_method: str,
    ip_address: str | None = None,
    device_fingerprint: str | None = None,
) -> dict:
    return FraudDetector(
        merchant_id=merchant_id,
        customer_email=customer_email,
        amount=amount,
        payment_method=payment_method,
        ip_address=ip_address,
        device_fingerprint=device_fingerprint,
    ).calculate()

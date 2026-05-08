"""
ML Fraud Scorer
----------------
Loads the trained XGBoost model and metadata produced by train_model.py
and exposes a single clean interface: MLFraudScorer.predict(...)

Returns a fraud probability (0.0 – 1.0) that FraudDetector combines
with its rule-based score.
"""

import os
import joblib
import numpy as np

# ── PATHS (relative to project root where uvicorn is launched) ──
_ML_DIR    = os.path.join("app", "ml")
_MODEL_PATH = os.path.join(_ML_DIR, "fraud_model.pkl")
_META_PATH  = os.path.join(_ML_DIR, "feature_meta.pkl")

# ── Payment methods → nearest PaySim transaction type ──
_PAYMENT_METHOD_MAP: dict[str, str] = {
    "card":          "PAYMENT",
    "bank_transfer": "TRANSFER",
    "ussd":          "CASH_OUT",
    "wallet":        "DEBIT",
}


class MLFraudScorer:
    """
    Wraps the trained XGBoost model.

    Usage:
        scorer = MLFraudScorer()               # loads model once
        prob   = scorer.predict(amount=5000, payment_method="card", hour=2)
        # prob -> float between 0.0 and 1.0
    """

    def __init__(self):
        if not os.path.exists(_MODEL_PATH) or not os.path.exists(_META_PATH):
            raise FileNotFoundError(
                "Trained model not found. Run: python train_model.py --dataset <path>"
            )

        self._model: object           = joblib.load(_MODEL_PATH)
        meta: dict                    = joblib.load(_META_PATH)
        self._feature_columns: list   = meta["feature_columns"]
        self._type_encoding: dict     = meta["type_encoding"]

    def _encode_payment_method(self, payment_method: str) -> int:
        """Map payment_method → PaySim type → integer encoding."""
        paysim_type = _PAYMENT_METHOD_MAP.get(payment_method, "PAYMENT")
        return self._type_encoding.get(paysim_type, 3)   # default → PAYMENT (3)

    def predict(
        self,
        amount: float,
        payment_method: str,
        hour: int,
    ) -> float:
        """
        Returns fraud probability (0.0 → 1.0).

        Parameters
        ----------
        amount          : transaction amount in Naira
        payment_method  : one of card | bank_transfer | ussd | wallet
        hour            : hour of day in WAT (0–23)
        """
        type_encoded = self._encode_payment_method(payment_method)

        # Build feature array in the exact same column order used during training:
        # ["amount", "type_encoded", "hour", "isFlaggedFraud"]
        # isFlaggedFraud is always 0 at inference time — we haven't made a
        # determination yet, and the rule engine handles that separately.
        features = np.array([[
            amount,
            type_encoded,
            hour,
            0,   # isFlaggedFraud
        ]], dtype=float)

        probability: float = float(self._model.predict_proba(features)[0][1])
        return probability


# ── Module-level singleton — loaded once when FastAPI starts ──
# FraudDetector imports this directly instead of instantiating per-request.
try:
    scorer = MLFraudScorer()
except FileNotFoundError:
    # Model not trained yet — scorer is None, FraudDetector will skip ML signal
    scorer = None

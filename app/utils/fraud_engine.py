from fastapi import FastAPI
from pydantic import BaseModel
import joblib
import numpy as np

# Load model and scaler
model = joblib.load("fraud_model.pkl")
scaler = joblib.load("scaler.pkl")

app = FastAPI(title="NewPay Fraud Engine v1")

# -----------------------------
# Request Model
# -----------------------------
class Transaction(BaseModel):
    features: list[float]


# -----------------------------
# Health Check Endpoint
# -----------------------------
@app.get("/health")
def health_check():
    return {"status": "Fraud Engine Running"}


# -----------------------------
# Fraud Prediction Endpoint
# -----------------------------
@app.post("/api/v1/fraud/predict")
def predict(transaction: Transaction):

    values = np.array(transaction.features).reshape(1, -1)
    values_scaled = scaler.transform(values)

    fraud_probability = model.predict_proba(values_scaled)[0][1]

    if fraud_probability > 0.9:
        decision = "BLOCK"
    elif fraud_probability > 0.7:
        decision = "REVIEW"
    else:
        decision = "APPROVE"

    return {
        "fraud_probability": float(fraud_probability),
        "decision": decision
    }
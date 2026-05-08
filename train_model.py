"""
PaySim Fraud Detection Model Trainer
-------------------------------------
Dataset : PaySim synthetic dataset (Kaggle)
          https://www.kaggle.com/datasets/ealaxi/paysim1
Output  : app/ml/fraud_model.pkl
           app/ml/feature_meta.pkl  (column order + type encoding map)

Usage:
    python train_model.py --dataset path/to/paysim.csv
"""

import argparse
import os
import joblib
import pandas as pd
from xgboost import XGBClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    classification_report,
    roc_auc_score,
    confusion_matrix,
)

# ── CONFIG ──
OUTPUT_DIR = os.path.join("app", "ml")
MODEL_PATH = os.path.join(OUTPUT_DIR, "fraud_model.pkl")
META_PATH  = os.path.join(OUTPUT_DIR, "feature_meta.pkl")

# PaySim transaction types → map to payment_method values
# (only the overlapping types matter; rest fall back to "other")
TYPE_ENCODING = {
    "CASH_OUT":  0,
    "TRANSFER":  1,
    "CASH_IN":   2,
    "PAYMENT":   3,
    "DEBIT":     4,
}

# Features used — must stay in this exact order at inference time
FEATURE_COLUMNS = [
    "amount",
    "type_encoded",
    "hour",
    "isFlaggedFraud",
]


def load_and_prepare(csv_path: str) -> tuple[pd.DataFrame, pd.Series]:
    print(f"Loading dataset from: {csv_path}")
    df = pd.read_csv(csv_path)

    print(f"  Rows loaded : {len(df):,}")
    print(f"  Fraud cases : {df['isFraud'].sum():,}  ({df['isFraud'].mean()*100:.2f}%)")

    # ── FEATURE ENGINEERING ──
    df["type_encoded"] = df["type"].map(TYPE_ENCODING).fillna(5).astype(int)
    df["hour"]         = df["step"] % 24   # step = hours elapsed; map back to hour-of-day

    X = df[FEATURE_COLUMNS].copy()
    y = df["isFraud"].copy()

    return X, y


def train(X: pd.DataFrame, y: pd.Series) -> XGBClassifier:
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    # Class imbalance: fraud is ~0.1% of PaySim — use scale_pos_weight
    neg = (y_train == 0).sum()
    pos = (y_train == 1).sum()
    scale = neg / pos
    print(f"\nClass imbalance ratio (scale_pos_weight): {scale:.1f}")

    model = XGBClassifier(
        n_estimators=300,
        max_depth=6,
        learning_rate=0.05,
        scale_pos_weight=scale,
        subsample=0.8,
        colsample_bytree=0.8,
        eval_metric="aucpr",
        random_state=42,
        n_jobs=-1,
    )

    print("\nTraining XGBoost model...")
    model.fit(
        X_train, y_train,
        eval_set=[(X_test, y_test)],
        verbose=50,
    )

    # ── EVALUATION ──
    y_pred  = model.predict(X_test)
    y_proba = model.predict_proba(X_test)[:, 1]

    print("\n── Evaluation Results ──")
    print(classification_report(y_test, y_pred, target_names=["Legit", "Fraud"]))
    print(f"ROC-AUC Score : {roc_auc_score(y_test, y_proba):.4f}")
    print(f"Confusion Matrix:\n{confusion_matrix(y_test, y_pred)}")

    # ── FEATURE IMPORTANCE ──
    importance = dict(zip(FEATURE_COLUMNS, model.feature_importances_))
    print("\nFeature Importances:")
    for feat, score in sorted(importance.items(), key=lambda x: -x[1]):
        print(f"  {feat:<20} {score:.4f}")

    return model


def save(model: XGBClassifier):
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    joblib.dump(model, MODEL_PATH)
    print(f"\nModel saved   → {MODEL_PATH}")

    meta = {
        "feature_columns": FEATURE_COLUMNS,
        "type_encoding":   TYPE_ENCODING,
    }
    joblib.dump(meta, META_PATH)
    print(f"Metadata saved → {META_PATH}")


def main():
    parser = argparse.ArgumentParser(description="Train PaySim fraud detection model")
    parser.add_argument(
        "--dataset",
        required=True,
        help="Path to the PaySim CSV file (e.g. data/paysim.csv)",
    )
    args = parser.parse_args()

    if not os.path.exists(args.dataset):
        raise FileNotFoundError(f"Dataset not found: {args.dataset}")

    X, y = load_and_prepare(args.dataset)
    model = train(X, y)
    save(model)
    print("\nDone. Run your FastAPI server and the model will be loaded automatically.")


if __name__ == "__main__":
    main()

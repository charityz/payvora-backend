import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, confusion_matrix
from sklearn.preprocessing import StandardScaler
import joblib


# Load dataset
data = pd.read_csv("creditcard.csv")

print("Dataset Loaded Successfully")
print(data.head())

# Separate features and target
X = data.drop("Class", axis=1)
y = data["Class"]

# Scale features
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)

# Split dataset
X_train, X_test, y_train, y_test = train_test_split(
    X_scaled, y, test_size=0.2, random_state=42
)

# Create model (balanced + more iterations)
model = LogisticRegression(
    max_iter=2000,
    class_weight="balanced"
)

# Train model
model.fit(X_train, y_train)

# Get probabilities instead of direct predictions
y_probs = model.predict_proba(X_test)[:, 1]

# Custom threshold (change this value to test)
threshold = 0.85

# Convert probabilities to 0 or 1 using threshold
y_pred_custom = (y_probs > threshold).astype(int)

print("\nConfusion Matrix:")
print(confusion_matrix(y_test, y_pred_custom))

print("\nClassification Report:")
print(classification_report(y_test, y_pred_custom))

# Save model and scaler
joblib.dump(model, "fraud_model.pkl")
joblib.dump(scaler, "scaler.pkl")

print("Model saved successfully!")
from pathlib import Path
from datetime import datetime, timezone
import json

import joblib
import numpy as np
import pandas as pd
import sklearn

from sklearn.ensemble import RandomForestClassifier


ROOT = Path(__file__).resolve().parents[1]

DATA_FILE = ROOT / "data" / "processed" / "app_training_data.csv"
ARTIFACT_DIR = ROOT / "artifacts"

MODEL_FILE = ARTIFACT_DIR / "random_forest.joblib"
METADATA_FILE = ARTIFACT_DIR / "model_metadata.json"


# Exact feature order used by our selected model
FEATURES = [
    "Daily_Return",
    "MA5_Ratio",
    "MA10_Ratio",
    "MA20_Ratio",
    "Momentum5",
    "Momentum10",
    "Volatility10",
    "Volatility20",
    "RSI",
    "Put_Call_Ratio",
    "Overnight_Gap",
    "Intraday_Return"
]


def main():

    ARTIFACT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    # Load historical training data
    if not DATA_FILE.exists():
        raise FileNotFoundError(
            f"Training data not found: {DATA_FILE}"
        )

    data = pd.read_csv(DATA_FILE)

    required_columns = FEATURES + ["Target", "Date"]

    missing_columns = [
        column for column in required_columns
        if column not in data.columns
    ]

    if missing_columns:
        raise ValueError(
            f"Missing required columns: {missing_columns}"
        )

    data["Date"] = pd.to_datetime(
        data["Date"],
        errors="raise"
    )

    X = data[FEATURES].copy()
    y = data["Target"].astype(int)

    # Validate data before training
    if X.empty:
        raise ValueError("Training dataset is empty.")

    if X.isnull().any().any():
        raise ValueError("Missing feature values detected.")

    if not np.isfinite(X.to_numpy(dtype=float)).all():
        raise ValueError("Infinite or non-numeric features detected.")

    if set(y.unique()) != {0, 1}:
        raise ValueError(
            "Training target must contain both classes: 0 and 1."
        )

    if len(X) != len(y):
        raise ValueError("Feature and target lengths do not match.")

    print("TRAINING DATA")
    print("Observations:", len(X))
    print("Features:", len(FEATURES))
    print("Date range:", data["Date"].min(), "to", data["Date"].max())

    print("\nTarget distribution:")
    print(
        y.value_counts().rename(
            index={0: "DOWN / FLAT", 1: "UP"}
        )
    )

    # Define our selected Random Forest
    model = RandomForestClassifier(
        n_estimators=200,
        max_depth=5,
        min_samples_split=10,
        min_samples_leaf=5,
        class_weight="balanced",
        random_state=42,
        n_jobs=-1
    )

    # Fit using all currently available labeled observations
    print("\nTraining Random Forest...")

    model.fit(X, y)

    # Save model
    joblib.dump(
        model,
        MODEL_FILE
    )

    # Save model metadata separately
    metadata = {
        "model_name": "Random Forest",
        "model_version": "1.0.0",
        "created_at_utc": datetime.now(
            timezone.utc
        ).isoformat(),
        "training_observations": int(len(X)),
        "training_start_date": data["Date"].min().strftime("%Y-%m-%d"),
        "training_end_date": data["Date"].max().strftime("%Y-%m-%d"),
        "features": FEATURES,
        "target_definition": (
            "1 = next S&P 500 trading-day return > 0; "
            "0 = next S&P 500 trading-day return <= 0"
        ),
        "prediction_threshold": 0.50,
        "target_counts": {
            "DOWN_FLAT": int((y == 0).sum()),
            "UP": int((y == 1).sum())
        },
        "model_parameters": model.get_params(),
        "sklearn_version": sklearn.__version__
    }

    with open(
        METADATA_FILE,
        "w",
        encoding="utf-8"
    ) as file:
        json.dump(
            metadata,
            file,
            indent=4
        )

    # Reload to verify that the artifact works
    loaded_model = joblib.load(MODEL_FILE)

    if list(loaded_model.feature_names_in_) != FEATURES:
        raise RuntimeError(
            "Saved model feature order does not match."
        )

    # Smoke test only, not a performance evaluation
    sample = X.iloc[[-1]]

    sample_probability = loaded_model.predict_proba(
        sample
    )[0]

    print("\nMODEL SAVED SUCCESSFULLY")
    print("Model:", MODEL_FILE)
    print("Metadata:", METADATA_FILE)

    print("\nArtifact verification:")
    print("Model reloaded successfully.")
    print("Feature count:", len(loaded_model.feature_names_in_))
    print("Sample UP probability:", round(sample_probability[1], 4))
    print("Sample DOWN probability:", round(sample_probability[0], 4))

    print(
        "\nNote: The sample prediction above uses a training observation. "
        "It is only a technical smoke test, not evidence of model accuracy."
    )


if __name__ == "__main__":
    main()

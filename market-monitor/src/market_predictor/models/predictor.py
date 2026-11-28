from pathlib import Path
from datetime import datetime, timezone
import json

import joblib
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[3]

MODEL_FILE = ROOT / "artifacts" / "random_forest.joblib"
METADATA_FILE = ROOT / "artifacts" / "model_metadata.json"

FEATURE_FILE = ROOT / "data" / "processed" / "app_feature_history.csv"
MARKET_FILE = ROOT / "data" / "raw" / "app_market_prices.csv"

PREDICTION_FILE = (
    ROOT / "data" / "processed" / "predictions.csv"
)


class PredictionNotReadyError(Exception):
    """Raised when no valid, unknown-outcome observation is available."""


def generate_prediction():
    """Generate and persist one prediction for the latest eligible session."""

    # Check required files
    for path in [MODEL_FILE, METADATA_FILE, FEATURE_FILE]:
        if not path.exists():
            raise FileNotFoundError(
                f"Required application file not found: {path}"
            )

    # Load model and metadata
    model = joblib.load(MODEL_FILE)

    with open(METADATA_FILE, "r", encoding="utf-8") as file:
        metadata = json.load(file)

    features = metadata["features"]
    threshold = float(metadata["prediction_threshold"])
    model_version = metadata["model_version"]

    # Validate feature order
    if list(model.feature_names_in_) != features:
        raise ValueError(
            "Model feature order does not match metadata."
        )

    # Load feature history
    data = pd.read_csv(FEATURE_FILE)

    required_columns = features + ["Date", "Target"]

    missing = [
        col for col in required_columns
        if col not in data.columns
    ]

    if missing:
        raise ValueError(
            f"Feature history is missing columns: {missing}"
        )

    data["Date"] = pd.to_datetime(
        data["Date"],
        errors="raise"
    )

    data["Target"] = pd.to_numeric(
        data["Target"],
        errors="coerce"
    )

    data = data.sort_values("Date").reset_index(drop=True)

    # Keep only complete feature observations
    data = data.dropna(
        subset=features
    ).copy()

    if data.empty:
        raise PredictionNotReadyError(
            "No complete feature observations are available."
        )

    # Only predict using the newest complete observation.
    # Its next-day outcome must still be unknown.
    latest = data.iloc[-1]

    if pd.notna(latest["Target"]):
        raise PredictionNotReadyError(
            "The latest complete feature date is "
            f"{latest['Date'].date()}, and its next-day outcome "
            "is already known. We need a newer complete observation "
            "with all 12 features and an unknown Target."
        )
    prediction_date = latest["Date"].strftime("%Y-%m-%d")
    

    # Ensure the prediction date is newer than model training data
    training_end = pd.Timestamp(
        metadata["training_end_date"]
    )

    if latest["Date"] <= training_end:
        raise PredictionNotReadyError(
            "The eligible feature date is not newer than the "
            "model's training cutoff. Retrain or collect newer data."
        )

    X_latest = pd.DataFrame(
        [latest[features].to_dict()],
        columns=features
    )

    X_latest = X_latest.astype(float)

    if not np.isfinite(X_latest.to_numpy()).all():
        raise ValueError(
            "Latest feature observation contains invalid values."
        )

    # Get model scores
    scores = model.predict_proba(X_latest)[0]

    class_scores = dict(
        zip(model.classes_, scores)
    )

    down_score = float(class_scores[0])
    up_score = float(class_scores[1])

    predicted_class = int(up_score >= threshold)

    direction = (
        "UP" if predicted_class == 1 else "DOWN / FLAT"
    )

    # Load prediction history
    if PREDICTION_FILE.exists():

        history = pd.read_csv(PREDICTION_FILE)

        duplicate = history[
            (history["prediction_date"] == prediction_date)
            & (history["model_version"] == model_version)
        ]

        if not duplicate.empty:
            print(
                f"Prediction already exists for {prediction_date}. "
                "No duplicate was created."
            )
            return duplicate.iloc[0].to_dict()

    else:
        history = pd.DataFrame()

    # Create prediction record
    record = {
        "prediction_date": prediction_date,
        "predicted_direction": direction,
        "predicted_class": predicted_class,
        "up_score": up_score,
        "down_score": down_score,
        "threshold": threshold,
        "model_version": model_version,
        "generated_at_utc": datetime.now(
            timezone.utc
        ).isoformat(),
        "outcome_date": None,
        "actual_direction": None,
        "actual_return": None,
        "status": "PENDING"
    }

    new_record = pd.DataFrame([record])

    if not history.empty:
        history = pd.concat(
            [history, new_record],
            ignore_index=True
        )
    else:
        history = new_record

    PREDICTION_FILE.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    history.to_csv(
        PREDICTION_FILE,
        index=False
    )

    print("\nPREDICTION GENERATED")
    print("Feature date:", prediction_date)
    print("Predicted direction:", direction)
    print("UP score:", f"{up_score:.4f}")
    print("DOWN score:", f"{down_score:.4f}")
    print("Threshold:", threshold)
    print("Model version:", model_version)
    print("Status: PENDING")
    print("Saved to:", PREDICTION_FILE)

    return record

from pathlib import Path

import pandas as pd
import math

ROOT = Path(__file__).resolve().parents[3]

PREDICTION_FILE = (
    ROOT / "data" / "processed" / "predictions.csv"
)

MARKET_FILE = (
    ROOT / "data" / "raw" / "app_market_prices.csv"
)


def update_prediction_outcomes():
    """Evaluate pending predictions when the next trading session closes."""

    if not PREDICTION_FILE.exists():
        print("No prediction history exists yet.")
        print("Outcome tracker is ready for future predictions.")
        return

    if not MARKET_FILE.exists():
        raise FileNotFoundError(
            f"Market data not found: {MARKET_FILE}"
        )

    predictions = pd.read_csv(PREDICTION_FILE)

    if predictions.empty:
        print("Prediction history is empty.")
        return

    market = pd.read_csv(MARKET_FILE)

    market["Date"] = pd.to_datetime(
        market["Date"]
    ).dt.normalize()

    market = (
        market
        .drop_duplicates(subset="Date")
        .sort_values("Date")
        .reset_index(drop=True)
    )

    # Create a lookup of each session's next S&P 500 trading date
    market["Next_Market_Date"] = market["Date"].shift(-1)

    market_lookup = market.set_index("Date")

    predictions["prediction_date"] = pd.to_datetime(
        predictions["prediction_date"]
    ).dt.normalize()

    updated_count = 0

    for index, prediction in predictions.iterrows():

        if prediction["status"] != "PENDING":
            continue

        prediction_date = prediction["prediction_date"]

        # Find the predicted session
        if prediction_date not in market_lookup.index:
            continue

        market_row = market_lookup.loc[prediction_date]

        next_date = market_row["Next_Market_Date"]

        # The next trading session has not closed yet
        if pd.isna(next_date):
            continue

        next_row = market_lookup.loc[next_date]

        current_close = float(
            market_row["SP500_Close"]
        )

        next_close = float(
            next_row["SP500_Close"]
        )

        if (
            not math.isfinite(current_close)
            or not math.isfinite(next_close)
            or current_close <= 0
            or next_close <= 0
):      
            print(
                f"Skipping {prediction_date.date()}: "
                "invalid closing price data."
            )
            continue

        # Calculate the actual next-session return
        actual_return = (
            next_close / current_close
        ) - 1

        actual_class = int(actual_return > 0)

        actual_direction = (
            "UP" if actual_class == 1 else "DOWN / FLAT"
        )

        # Compare against the saved prediction
        predicted_class = int(
            prediction["predicted_class"]
        )

        predictions.at[index, "outcome_date"] = (
            next_date.strftime("%Y-%m-%d")
        )

        predictions.at[index, "actual_direction"] = (
            actual_direction
        )

        predictions.at[index, "actual_return"] = (
            actual_return
        )

        predictions.at[index, "actual_class"] = (
            actual_class
        )

        predictions.at[index, "correct"] = (
            predicted_class == actual_class
        )

        predictions.at[index, "status"] = "EVALUATED"

        updated_count += 1

    # Save updated prediction history
    predictions["prediction_date"] = (
        predictions["prediction_date"]
        .dt.strftime("%Y-%m-%d")
    )

    predictions.to_csv(
        PREDICTION_FILE,
        index=False
    )

    # Display summary
    evaluated = predictions[
        predictions["status"] == "EVALUATED"
    ]

    pending = predictions[
        predictions["status"] == "PENDING"
    ]

    print("\nPREDICTION OUTCOME UPDATE")
    print("Newly evaluated predictions:", updated_count)
    print("Total evaluated predictions:", len(evaluated))
    print("Still pending:", len(pending))

    if not evaluated.empty:

        correct_values = (
        evaluated["correct"]
        .astype(str)
        .str.strip()
        .str.lower()
        .map({"true": True, "false": False})
        )

        valid_correct = correct_values.dropna()

        if not valid_correct.empty:
            accuracy = valid_correct.mean()

            print(
                "Historical prediction accuracy:",
                f"{accuracy:.2%}"
            )
        else:
            print("Accuracy unavailable: no valid outcomes.")

        print("\nMost recent evaluated predictions:")

        print(
            evaluated.tail(5)[
                [
                    "prediction_date",
                    "predicted_direction",
                    "actual_direction",
                    "actual_return",
                    "correct"
                ]
            ].to_string(index=False)
        )

    print("\nSaved:", PREDICTION_FILE)

    return predictions

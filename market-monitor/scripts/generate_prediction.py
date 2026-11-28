from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from market_predictor.models.predictor import (
    generate_prediction,
    PredictionNotReadyError
)


if __name__ == "__main__":

    try:
        generate_prediction()

    except PredictionNotReadyError as error:
        print("\nPREDICTION NOT READY")
        print(error)

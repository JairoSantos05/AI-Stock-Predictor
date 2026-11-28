from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from market_predictor.storage.outcomes import update_prediction_outcomes


if __name__ == "__main__":
    update_prediction_outcomes()

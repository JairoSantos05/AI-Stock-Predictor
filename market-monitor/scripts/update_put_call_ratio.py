from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from market_predictor.data.cboe_data import update_put_call_ratio


if __name__ == "__main__":
    update_put_call_ratio(lookback_sessions=10)

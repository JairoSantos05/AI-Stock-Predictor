from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from market_predictor.data.market_data import update_market_prices


if __name__ == "__main__":
    data = update_market_prices(period="10d")

    print("\nMost recent observations:")
    print(data.tail(5).to_string(index=False))

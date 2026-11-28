import yfinance as yf
import pandas as pd
from pathlib import Path


def download_sp500_data(period="10y"):
    print("Downloading S&P 500 historical data...")

    ticker = yf.Ticker("^GSPC")

    data = ticker.history(
        period=period,
        interval="1d",
        auto_adjust=True
    )

    if data.empty:
        raise ValueError("No data was downloaded.")

    # Convert dates to New York local time
    data = data.reset_index()

    data["Date"] = pd.to_datetime(
        data["Date"], utc=True
    ).dt.tz_convert("America/New_York").dt.tz_localize(None)

    return data


if __name__ == "__main__":
    # Find the main project directory
    project_dir = Path(__file__).resolve().parents[1]

    # Download historical data
    data = download_sp500_data()

    # Create raw data directory
    output_dir = project_dir / "data" / "raw"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Save dataset
    output_file = output_dir / "sp500.csv"
    data.to_csv(output_file, index=False)

    print("\nDownload successful!")
    print(f"Total observations: {len(data)}")
    print(f"Saved to: {output_file}")

    print("\nFirst five rows:")
    print(data.head())
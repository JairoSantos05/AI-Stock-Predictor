from pathlib import Path

import pandas as pd
import yfinance as yf


PROJECT_ROOT = Path(__file__).resolve().parents[3]
RAW_DATA_DIR = PROJECT_ROOT / "data" / "raw"
OUTPUT_FILE = RAW_DATA_DIR / "app_market_prices.csv"

TICKERS = {
    "^GSPC": "SP500",
    "^VIX": "VIX",
    "^IXIC": "NASDAQ",
}


def fetch_ticker_history(symbol: str, period: str = "10d") -> pd.DataFrame:
    """Download and normalize daily history for one Yahoo Finance ticker."""

    history = yf.Ticker(symbol).history(
        period=period,
        interval="1d",
        auto_adjust=False,
        actions=False,
        repair=False,
        timeout=30,
    )

    if history.empty:
        raise RuntimeError(f"No market data returned for {symbol}")

    history = history.copy()

    # Normalize all dates to New York trading dates
    dates = pd.DatetimeIndex(history.index)

    if dates.tz is not None:
        dates = dates.tz_convert(
            "America/New_York"
        ).tz_localize(None)

    history.index = dates.normalize()
    history.index.name = "Date"

    history = history[
        ~history.index.duplicated(keep="last")
    ]

    return history.sort_index()


def download_recent_market_data(period: str = "10d") -> pd.DataFrame:
    """Download S&P 500 OHLCV, VIX close, and NASDAQ close."""

    histories = {}

    for symbol in TICKERS:
        print(f"Downloading {symbol}...")

        histories[symbol] = fetch_ticker_history(
            symbol,
            period=period
        )

    # S&P 500 price and volume data
    sp500 = histories["^GSPC"]

    required_sp500_columns = [
        "Open",
        "High",
        "Low",
        "Close",
        "Volume"
    ]

    missing = [
        col for col in required_sp500_columns
        if col not in sp500.columns
    ]

    if missing:
        raise ValueError(
            f"S&P 500 data is missing columns: {missing}"
        )

    sp500 = sp500[required_sp500_columns].rename(
        columns={
            "Open": "SP500_Open",
            "High": "SP500_High",
            "Low": "SP500_Low",
            "Close": "SP500_Close",
            "Volume": "SP500_Volume",
        }
    )

    # VIX and NASDAQ closing values
    vix = histories["^VIX"]["Close"].rename("VIX")
    nasdaq = histories["^IXIC"]["Close"].rename("NASDAQ")

    # Keep only dates available across all three sources
    market_data = pd.concat(
        [sp500, vix, nasdaq],
        axis=1,
        join="inner"
    )

    # Exclude today's potentially incomplete daily candle
    now_et = pd.Timestamp.now(
    tz="America/New_York"
    )
    
    # Convert to a timezone-naive New York date
    cutoff_date = now_et.tz_localize(None).normalize()
    
    # Before 4:15 PM Eastern, exclude today's potentially incomplete candle
    if now_et.time() < pd.Timestamp("16:15").time():
        cutoff_date -= pd.Timedelta(days=1)

    market_data = market_data.loc[
        market_data.index <= cutoff_date
    ]

    market_data = market_data.dropna().sort_index()

    if market_data.empty:
        raise RuntimeError(
            "No complete market dates were available."
        )

    return market_data.reset_index()


def update_market_prices(
    period: str = "10d"
) -> pd.DataFrame:
    """
    Fetch recent market data and merge it into the app's CSV.
    Existing research CSV files are not modified.
    """

    RAW_DATA_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    new_data = download_recent_market_data(period)

    new_data["Date"] = pd.to_datetime(
        new_data["Date"]
    ).dt.strftime("%Y-%m-%d")

    if OUTPUT_FILE.exists():

        existing_data = pd.read_csv(
            OUTPUT_FILE
        )

        required_columns = new_data.columns.tolist()

        if not set(required_columns).issubset(
            existing_data.columns
        ):
            raise ValueError(
                "Existing application market data has "
                "an unexpected schema. Inspect the file "
                "before replacing it."
            )

        existing_data["Date"] = pd.to_datetime(
            existing_data["Date"]
        ).dt.strftime("%Y-%m-%d")

        combined_data = pd.concat(
            [
                existing_data[required_columns],
                new_data
            ],
            ignore_index=True
        )

    else:
        combined_data = new_data.copy()

    # Replace overlapping dates with the latest downloaded values
    combined_data = (
        combined_data
        .drop_duplicates(subset="Date", keep="last")
        .sort_values("Date")
        .reset_index(drop=True)
    )

    combined_data.to_csv(
        OUTPUT_FILE,
        index=False
    )

    print("\nMarket data saved successfully.")
    print("File:", OUTPUT_FILE)
    print("Total stored observations:", len(combined_data))
    print("Latest trading date:", combined_data["Date"].iloc[-1])

    return combined_data

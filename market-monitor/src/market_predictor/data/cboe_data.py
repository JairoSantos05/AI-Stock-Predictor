from pathlib import Path
from io import StringIO
import time

import pandas as pd
import requests


PROJECT_ROOT = Path(__file__).resolve().parents[3]
RAW_DATA_DIR = PROJECT_ROOT / "data" / "raw"

MARKET_FILE = RAW_DATA_DIR / "app_market_prices.csv"
OUTPUT_FILE = RAW_DATA_DIR / "app_put_call_ratio.csv"

CBOE_URL = (
    "https://www.cboe.com/markets/us/options/"
    "market-statistics/daily"
)

# Verified against the returned CBOE HTML.
SPX_TABLE_INDEX = 6


def fetch_daily_put_call_ratio(date_str, session):
    """Retrieve SPX-related options volume for one trading date."""

    response = session.get(
        CBOE_URL,
        params={"dt": date_str},
        headers={"User-Agent": "Mozilla/5.0"},
        timeout=30
    )

    response.raise_for_status()

    try:
        tables = pd.read_html(StringIO(response.text))
    except ValueError:
        # CBOE has not published parseable tables for this date.
        return None

    if len(tables) <= SPX_TABLE_INDEX:
        return None

    options_table = tables[SPX_TABLE_INDEX].copy()

    # Normalize column names
    if isinstance(options_table.columns, pd.MultiIndex):
        options_table.columns = [
            str(col[-1]).strip()
            for col in options_table.columns
        ]
    else:
        options_table.columns = [
            str(col).strip()
            for col in options_table.columns
        ]

    required_columns = {"Name", "Call", "Put"}

    if not required_columns.issubset(
        options_table.columns
    ):
        raise ValueError(
            f"Unexpected CBOE table structure for {date_str}: "
            f"{options_table.columns.tolist()}"
        )

    # Extract VOLUME, never OPEN INTEREST
    volume_rows = options_table[
        options_table["Name"]
        .astype(str)
        .str.strip()
        .str.upper()
        .eq("VOLUME")
    ]

    if len(volume_rows) != 1:
        raise ValueError(
            f"Expected one VOLUME row for {date_str}; "
            f"found {len(volume_rows)}."
        )

    volume_row = volume_rows.iloc[0]

    call_volume = float(
        str(volume_row["Call"]).replace(",", "")
    )

    put_volume = float(
        str(volume_row["Put"]).replace(",", "")
    )

    if call_volume <= 0 or put_volume < 0:
        raise ValueError(
            f"Invalid options volume for {date_str}."
        )

    return {
        "Date": date_str,
        "Call_Volume": call_volume,
        "Put_Volume": put_volume,
        "Put_Call_Ratio": put_volume / call_volume
    }


def update_put_call_ratio(lookback_sessions=10):
    """Collect missing recent CBOE observations and save them."""

    if not MARKET_FILE.exists():
        raise FileNotFoundError(
            f"Market data file not found: {MARKET_FILE}"
        )

    market = pd.read_csv(MARKET_FILE)

    trading_dates = (
        pd.to_datetime(market["Date"])
        .drop_duplicates()
        .sort_values()
        .tail(lookback_sessions)
        .sort_values(ascending=False)
    )

    # Load existing application data
    if OUTPUT_FILE.exists():

        existing = pd.read_csv(OUTPUT_FILE)

        existing["Date"] = pd.to_datetime(
            existing["Date"]
        ).dt.strftime("%Y-%m-%d")

        completed_dates = set(existing["Date"])

    else:
        existing = pd.DataFrame(
            columns=[
                "Date",
                "Call_Volume",
                "Put_Volume",
                "Put_Call_Ratio"
            ]
        )
        completed_dates = set()

    new_records = []

    session = requests.Session()

    for trading_date in trading_dates:

        date_str = trading_date.strftime("%Y-%m-%d")

        if date_str in completed_dates:
            continue

        print(f"Checking CBOE data for {date_str}...")

        try:
            result = fetch_daily_put_call_ratio(
                date_str,
                session
            )

            if result is None:
                print(
                    f"No CBOE options table available for "
                    f"{date_str}. Will retry later."
                )
                continue

            new_records.append(result)

            print(
                f"Put/Call Ratio: "
                f"{result['Put_Call_Ratio']:.4f}"
            )

        except requests.RequestException as error:
            print(
                f"Request failed for {date_str}: {error}"
            )

        except Exception as error:
            print(
                f"Could not process {date_str}: {error}"
            )

        time.sleep(0.5)

    # Combine existing and new records
    if new_records:

        new_data = pd.DataFrame(new_records)

        combined = pd.concat(
            [existing, new_data],
            ignore_index=True
        )

    else:
        combined = existing.copy()

    if not combined.empty:

        combined = (
            combined
            .drop_duplicates(
                subset="Date",
                keep="last"
            )
            .sort_values("Date")
            .reset_index(drop=True)
        )

        RAW_DATA_DIR.mkdir(
            parents=True,
            exist_ok=True
        )

        combined.to_csv(
            OUTPUT_FILE,
            index=False
        )

    print("\nCBOE collection finished.")
    print("New observations:", len(new_records))
    print("Total stored observations:", len(combined))
    print("Output file:", OUTPUT_FILE)

    if not combined.empty:
        print("\nMost recent observations:")
        print(combined.tail(5).to_string(index=False))

    return combined

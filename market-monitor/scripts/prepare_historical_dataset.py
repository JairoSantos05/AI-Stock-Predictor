from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
PROCESSED = ROOT / "data" / "processed"

PROCESSED.mkdir(parents=True, exist_ok=True)


def load_data(filename):
    """Load a CSV and normalize its trading dates."""

    path = RAW / filename

    if not path.exists():
        raise FileNotFoundError(f"Missing file: {path}")

    df = pd.read_csv(path)

    if "Date" not in df.columns:
        raise ValueError(f"No Date column in {filename}")

    df["Date"] = pd.to_datetime(
        df["Date"],
        errors="raise"
    ).dt.normalize()

    if df["Date"].duplicated().any():
        raise ValueError(f"Duplicate dates in {filename}")

    return df


def combine_recent_data(historical, recent, columns):
    """Combine historical and recent data, preferring recent overlaps."""

    combined = pd.concat(
        [
            historical[["Date"] + columns],
            recent[["Date"] + columns]
        ],
        ignore_index=True
    )

    return (
        combined
        .drop_duplicates(subset="Date", keep="last")
        .sort_values("Date")
        .reset_index(drop=True)
    )


# --------------------------------------------------
# 1. Load the historical and recently collected data
# --------------------------------------------------

sp500_hist = load_data("sp500.csv")

market_hist = load_data("market_indicators.csv")

put_call_hist = load_data("put_call_ratio_daily.csv")

app_market = load_data("app_market_prices.csv")

app_put_call = load_data("app_put_call_ratio.csv")


# --------------------------------------------------
# 2. Combine S&P 500 price data
# --------------------------------------------------

sp500_recent = app_market.rename(
    columns={
        "SP500_Open": "Open",
        "SP500_High": "High",
        "SP500_Low": "Low",
        "SP500_Close": "Close",
        "SP500_Volume": "Volume"
    }
)

price_columns = [
    "Open",
    "High",
    "Low",
    "Close",
    "Volume"
]

sp500 = combine_recent_data(
    sp500_hist,
    sp500_recent,
    price_columns
)


# --------------------------------------------------
# 3. Combine VIX and NASDAQ data
# --------------------------------------------------

market = combine_recent_data(
    market_hist,
    app_market,
    ["VIX", "NASDAQ"]
)

# Keep only actual S&P 500 trading dates.
# This removes dates such as holidays when only
# the VIX or NASDAQ data may be present.
market = market[
    market["Date"].isin(sp500["Date"])
].copy()

market = market.sort_values(
    "Date"
).reset_index(drop=True)

# Calculate changes across consecutive S&P 500 sessions.
market["VIX_Change"] = market["VIX"].pct_change(
    fill_method=None
)

market["NASDAQ_Return"] = market["NASDAQ"].pct_change(
    fill_method=None
)


# --------------------------------------------------
# 4. Combine historical and recent Put/Call data
# --------------------------------------------------

put_call = combine_recent_data(
    put_call_hist,
    app_put_call,
    [
        "Call_Volume",
        "Put_Volume",
        "Put_Call_Ratio"
    ]
)

# Validate the ratio definition.
expected_ratio = (
    put_call["Put_Volume"] /
    put_call["Call_Volume"]
)

if not np.allclose(
    put_call["Put_Call_Ratio"],
    expected_ratio,
    rtol=1e-6,
    atol=1e-8
):
    raise ValueError(
        "Put/Call ratios do not match Put Volume / Call Volume."
    )


# --------------------------------------------------
# 5. Calculate technical features on full S&P history
# --------------------------------------------------

previous_close = sp500["Close"].shift(1)

# Daily return
sp500["Daily_Return"] = sp500["Close"].pct_change(
    fill_method=None
)

# Moving averages
sp500["MA5"] = sp500["Close"].rolling(5).mean()
sp500["MA10"] = sp500["Close"].rolling(10).mean()
sp500["MA20"] = sp500["Close"].rolling(20).mean()

# Moving average ratios
sp500["MA5_Ratio"] = (
    sp500["Close"] / sp500["MA5"]
) - 1

sp500["MA10_Ratio"] = (
    sp500["Close"] / sp500["MA10"]
) - 1

sp500["MA20_Ratio"] = (
    sp500["Close"] / sp500["MA20"]
) - 1

# Momentum
sp500["Momentum5"] = sp500["Close"].pct_change(
    5,
    fill_method=None
)

sp500["Momentum10"] = sp500["Close"].pct_change(
    10,
    fill_method=None
)

# Volatility
sp500["Volatility10"] = (
    sp500["Daily_Return"]
    .rolling(10)
    .std()
)

sp500["Volatility20"] = (
    sp500["Daily_Return"]
    .rolling(20)
    .std()
)

# RSI
delta = sp500["Close"].diff()

gain = delta.clip(lower=0)
loss = -delta.clip(upper=0)

average_gain = gain.rolling(14).mean()
average_loss = loss.rolling(14).mean()

relative_strength = average_gain / average_loss

sp500["RSI"] = (
    100 - (100 / (1 + relative_strength))
)

# Overnight gap
sp500["Overnight_Gap"] = (
    sp500["Open"] - previous_close
) / previous_close

# Intraday return
sp500["Intraday_Return"] = (
    sp500["Close"] - sp500["Open"]
) / sp500["Open"]


# --------------------------------------------------
# 6. Create the next-trading-day prediction target
# --------------------------------------------------

# Important: Calculate this BEFORE joining CBOE data.
# The next observation must be the next S&P 500
# trading session, not the next available CBOE date.

sp500["Next_Day_Return"] = (
    sp500["Daily_Return"].shift(-1)
)

sp500["Target"] = np.where(
    sp500["Next_Day_Return"].notna(),
    (sp500["Next_Day_Return"] > 0).astype(int),
    np.nan
)


# --------------------------------------------------
# 7. Merge all sources
# --------------------------------------------------

combined = sp500.merge(
    market,
    on="Date",
    how="left",
    validate="one_to_one"
)

combined = combined.merge(
    put_call,
    on="Date",
    how="left",
    validate="one_to_one"
)


# --------------------------------------------------
# 8. Define the exact 12 model features
# --------------------------------------------------

model_features = [
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


# Retain observations with all 12 features.
# The last row may have no target yet, which is okay:
# it can become a prediction observation once complete.

feature_history = combined.dropna(
    subset=model_features
).copy()

feature_history["Target"] = (
    feature_history["Target"].astype("Int64")
)

feature_history = (
    feature_history
    .sort_values("Date")
    .reset_index(drop=True)
)


# Training requires both complete features and a known outcome.
training_data = feature_history.dropna(
    subset=["Target"]
).copy()

training_data["Target"] = (
    training_data["Target"].astype(int)
)


# --------------------------------------------------
# 9. Save application datasets
# --------------------------------------------------

feature_file = PROCESSED / "app_feature_history.csv"

training_file = PROCESSED / "app_training_data.csv"

feature_history.to_csv(
    feature_file,
    index=False
)

training_data.to_csv(
    training_file,
    index=False
)


# --------------------------------------------------
# 10. Print validation report
# --------------------------------------------------

print("\nHISTORICAL DATA INITIALIZATION COMPLETE")

print("\nS&P 500 observations:", len(sp500))
print("Market indicator observations:", len(market))
print("Put/Call observations:", len(put_call))

print("\nFeature history observations:", len(feature_history))
print("Training observations:", len(training_data))
print("Number of model features:", len(model_features))

print("\nFeature date range:")
print(
    feature_history["Date"].min(),
    "to",
    feature_history["Date"].max()
)

print("\nTraining date range:")
print(
    training_data["Date"].min(),
    "to",
    training_data["Date"].max()
)

print("\nTarget distribution:")
print(
    training_data["Target"]
    .value_counts()
    .rename(index={
        0: "DOWN / FLAT",
        1: "UP"
    })
)

print("\nMissing values in model features:")
print(feature_history[model_features].isnull().sum())

print("\nLatest feature observations:")
print(
    feature_history[
        ["Date", "Close"] + model_features[-3:] + ["Target"]
    ].tail(5).to_string(index=False)
)

print("\nFiles saved:")
print(feature_file)
print(training_file)

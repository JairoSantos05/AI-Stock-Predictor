# S&P 500 Market Monitor

An experimental Streamlit application that uses a Random Forest model to estimate whether the next S&P 500 trading session will close **UP** or **DOWN / FLAT**. The dashboard displays market data, model output, and prediction results.


## Requirements

- Windows 10 or 11
- Python 3.11 (developed with Python 3.11.9)
- Visual Studio Code with the Microsoft Python extension
- Internet connection for Yahoo Finance and CBOE data
- No API keys, accounts, or environment variables required

## Setup in VS Code

1. Clone the repository and open the `StockMarket` folder in VS Code:

   ```powershell
   git clone https://github.com/NickCharlieR/StockMarket.git
   cd StockMarket
   ```

2. Open **Terminal → New Terminal**. Create and activate a virtual environment:

   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

   If PowerShell blocks activation, run this once in that terminal and activate again:

   ```powershell
   Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
   .\.venv\Scripts\Activate.ps1
   ```

3. Install dependencies and select the `.venv` interpreter in VS Code (`Ctrl+Shift+P` → **Python: Select Interpreter**):

   ```powershell
   python -m pip install -r requirements.txt
   ```

## Run the application

From the project root, with `.venv` activated:

```powershell
python -m streamlit run app.py
```

Open <http://localhost:8501> if the browser does not open automatically. Press `Ctrl+C` in the terminal to stop the app.

## Update market data

Click **Update market data** in the dashboard, or run the complete update from the terminal:

```powershell
python scripts/daily_update.py
```

The update downloads S&P 500, VIX, and NASDAQ data from Yahoo Finance; retrieves the SPX Put/Call Ratio from CBOE when published; rebuilds features; evaluates pending predictions; and creates a new prediction when eligible data is available.

CBOE data can be published later than market prices. If the latest session's Put/Call Ratio is unavailable, the app waits rather than filling in missing data or predicting from an older session. A **Prediction not ready** message can therefore be normal.

## Model and data

The saved model is in `artifacts/`. It uses 12 inputs: daily return; 5-, 10-, and 20-day moving-average ratios; 5- and 10-day momentum; 10- and 20-day volatility; RSI; SPX Put/Call Ratio; overnight gap; and intraday return. VIX and NASDAQ are displayed in the dashboard but are **not** inputs to the current model.

Yahoo Finance supplies `^GSPC`, `^VIX`, and `^IXIC`. CBOE supplies SPX options volume; Put/Call Ratio is calculated as put volume divided by call volume. The model is not retrained during daily updates.

## Project files

- `app.py` — Streamlit dashboard
- `requirements.txt` — Python dependencies
- `artifacts/` — saved model and metadata
- `data/raw/` — historical and recent source data
- `data/processed/` — generated features, training data, and prediction history
- `scripts/` — data collection, feature preparation, training, prediction, and outcome-update scripts
- `src/market_predictor/` — application data, model, and storage code
- `notebooks/` — model experiments

For an intentional model retraining, run `python scripts/train_model.py`. This replaces the saved model; it is not part of the normal daily update.

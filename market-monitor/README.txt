S&P 500 MARKET MONITOR
======================

This ZIP contains the complete source code for an experimental S&P 500 market
monitor. It uses a saved Random Forest model to estimate the direction of the
next S&P 500 trading session and provides a Streamlit dashboard for viewing
market data and prediction results.

SYSTEM REQUIREMENTS
------------------
- Windows 10 or 11
- Python 3.11
- Visual Studio Code (recommended) with the Microsoft Python extension
- Internet connection for Yahoo Finance and CBOE data
- No API keys, accounts, or environment variables are required

INSTALLATION
------------
1. Extract the ZIP file to a folder on your computer.
2. Open Visual Studio Code. Select File > Open Folder and choose the extracted
   project folder. The folder should contain app.py and requirements.txt.
3. Open Terminal > New Terminal in VS Code.
4. Create and activate a virtual environment:

      python -m venv .venv
      .\.venv\Scripts\Activate.ps1

   If PowerShell blocks activation, run the following command in that terminal,
   then activate the environment again:

      Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
      .\.venv\Scripts\Activate.ps1

5. Install the required packages:

      python -m pip install -r requirements.txt

6. In VS Code, press Ctrl+Shift+P, select "Python: Select Interpreter", and
   choose the Python interpreter inside the project's .venv folder.

RUN THE APPLICATION
-------------------
With the virtual environment active and the terminal in the project folder,
run:

      python -m streamlit run app.py

The dashboard opens in your browser. If it does not open automatically, visit:

      http://localhost:8501

To stop the application, return to the terminal and press Ctrl+C.

UPDATING DATA
-------------
Use the "Update market data" button in the dashboard, or run:

      python scripts/daily_update.py

The update downloads S&P 500, VIX, and NASDAQ data from Yahoo Finance, retrieves
the SPX Put/Call Ratio from CBOE when available, rebuilds the model features,
evaluates pending predictions, and generates a new prediction when eligible
data is available.

CBOE may publish its daily options data after market prices are available. If
the latest Put/Call Ratio has not been published, the application waits for it
rather than filling in missing data or using an older value. A "Prediction not
ready" message can therefore be expected until all required data is available.

MODEL AND DATA NOTES
-------------------
The saved Random Forest model and its metadata are included in the artifacts
folder. The model uses 12 inputs, including S&P 500 returns, moving-average
ratios, momentum, volatility, RSI, SPX Put/Call Ratio, overnight gap, and
intraday return. VIX and NASDAQ are shown in the dashboard but are not inputs
to the current model. Daily updates do not retrain the model.

This is an academic research project. Model scores are experimental, are not
calibrated probabilities, and should not be treated as investment advice or
trading signals.

PROJECT CONTENTS
----------------
app.py                         Streamlit dashboard
requirements.txt               Python dependencies
artifacts/                      Saved model and model metadata
data/raw/                       Source market and options data
data/processed/                 Features, training data, prediction history
scripts/                        Data, training, prediction, and update scripts
src/market_predictor/           Application source code
notebooks/                      Model experiments

OPTIONAL: RETRAINING THE MODEL
-----------------------------
To intentionally retrain the model using the prepared training data, run:

      python scripts/train_model.py

This replaces the saved model. Retraining is not part of the normal daily
update process.

CREDENTIALS
-----------
No login, test account, or credentials are required.

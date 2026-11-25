import streamlit as st
import pandas as pd

# --- TEMPORARY MOCK FUNCTION (Replace with teammates' import later) ---
def get_mock_prediction(ticker):
    fake_state = pd.DataFrame([{
        "Close": 185.20,
        "SMA_10": 182.50,
        "SMA_50": 176.80,
        "Daily_Return (%)": 1.25
    }])
    return {
        "prob_up": 0.68,
        "model_accuracy": 0.56,
        "current_state": fake_state
    }
# ----------------------------------------------------------------------

st.title("AI Stock Predictor")
ticker = st.selectbox("Select Stock Ticker", ["AAPL", "MSFT", "NVDA"])

if st.button("Run Prediction"):
    result = get_mock_prediction(ticker)
    prob_up = result["prob_up"]
    confidence = prob_up * 100

    if prob_up >= 0.60:
        action = "BUY"
    elif prob_up <= 0.40:
        action = "DON'T BUY"
    else:
        action = "HOLD"

    col1, col2, col3 = st.columns(3)
    col1.metric("Recommendation", action)
    col2.metric("Confidence", f"{confidence:.1f}%")
    col3.metric("Model Accuracy", f"{result['model_accuracy'] * 100:.1f}%")

    st.subheader(f"Current State of {ticker}")
    st.dataframe(result["current_state"], hide_index=True)
from pathlib import Path
import subprocess
import sys

import pandas as pd
import plotly.graph_objects as go
import streamlit as st


# --------------------------------------------------
# App setup
# --------------------------------------------------

ROOT = Path(__file__).resolve().parent
RAW = ROOT / "data" / "raw"
PROCESSED = ROOT / "data" / "processed"

st.set_page_config(
    page_title="S&P 500 Market Monitor",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Keep styling simple. Streamlit supplies the background, text, borders,
# inputs, and chart theme for whichever Light/Dark setting is selected.
st.markdown(
    """
    <style>
    .stApp { font-family: "Segoe UI", Arial, sans-serif; }
    .block-container { padding: 1.5rem 2rem 3rem; max-width: 1500px; }
    h1 { font-size: 1.9rem !important; font-weight: 680 !important; }
    h2 { font-size: 1.3rem !important; font-weight: 630 !important; }
    [data-testid="stMetricValue"] { font-size: 1.7rem; font-weight: 650; }
    [data-testid="stMetricLabel"] { font-size: 0.78rem; font-weight: 600; }

    /* The brand blue is the only fixed UI color. */
    .stButton button[kind="primary"] {
        background: #29445B !important;
        color: #FFFFFF !important;
        border: 1px solid #29445B !important;
        border-radius: 5px !important;
        min-height: 2.45rem;
        font-weight: 650 !important;
    }
    .stButton button[kind="primary"]:hover {
        background: #20374B !important;
        border-color: #20374B !important;
    }

    /* Keep range buttons readable without overriding the active theme. */
    .stButton button { white-space: nowrap; }

    .brand-logo-slot {
        width: 52px;
        height: 52px;
        border: 1px solid rgba(128, 145, 158, 0.55);
        border-radius: 6px;
    }
    .brand-name { font-size: 1rem; font-weight: 700; line-height: 1.2; }
    .brand-description { font-size: 0.72rem; opacity: 0.72; }
    section[data-testid="stSidebar"] .block-container { padding: 1.2rem 1rem 2rem; }
    hr { margin: 1.25rem 0; }
    </style>
    """,
    unsafe_allow_html=True,
)


# --------------------------------------------------
# Helpers
# --------------------------------------------------

def load_csv(path):
    if not path.exists():
        return pd.DataFrame()
    data = pd.read_csv(path)
    if "Date" in data.columns:
        data["Date"] = pd.to_datetime(data["Date"], errors="coerce")
    return data


def fmt(value, decimals=2):
    if value is None or pd.isna(value):
        return "N/A"
    return f"{value:,.{decimals}f}"


def fmt_date(value):
    if value is None or pd.isna(value):
        return "Unavailable"
    return pd.Timestamp(value).strftime("%b %d, %Y")


def normalize_direction(value):
    value = str(value).strip().upper()
    if value == "UP":
        return "UP"
    if value in {"DOWN", "FLAT", "DOWN / FLAT", "DOWN/FLAT"}:
        return "DOWN / FLAT"
    return None


def parse_bool(series):
    return (
        series.astype(str).str.strip().str.lower()
        .map({"true": True, "false": False, "1": True, "0": False})
    )


def add_line_chart(data, column, label, y_title, color, hover_format, height=340,
                   date_start=None, date_end=None, reference_line=False):
    """Build a Plotly chart that inherits the active Streamlit theme."""
    values = pd.to_numeric(data[column], errors="coerce")
    valid = data.loc[values.notna()].copy()
    valid[column] = values.loc[values.notna()]

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=valid["Date"],
            y=valid[column],
            mode="lines+markers" if len(valid) == 1 else "lines",
            name=label,
            line={"color": color, "width": 2},
            marker={"size": 6},
            hovertemplate=f"%{{x|%b %d, %Y}}<br>{hover_format}<extra></extra>",
        )
    )

    if reference_line:
        fig.add_hline(
            y=1.0,
            line_dash="dot",
            line_color="#8998A6",
            annotation_text="1.0 · equal put and call volume",
            annotation_position="bottom right",
        )

    fig.update_layout(
        height=height,
        margin={"l": 8, "r": 8, "t": 12, "b": 8},
        xaxis_title=None,
        yaxis_title=y_title,
        hovermode="x unified",
        showlegend=False,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    fig.update_xaxes(showgrid=False, zeroline=False)
    fig.update_yaxes(zeroline=False)

    if date_start is not None and date_end is not None:
        if pd.Timestamp(date_start) == pd.Timestamp(date_end):
            center = pd.Timestamp(date_start)
            fig.update_xaxes(range=[center - pd.Timedelta(hours=12), center + pd.Timedelta(hours=12)])
        else:
            fig.update_xaxes(range=[date_start, date_end])

    return fig


# --------------------------------------------------
# Load data
# --------------------------------------------------

market = load_csv(RAW / "app_market_prices.csv")
put_call = load_csv(RAW / "app_put_call_ratio.csv")
features = load_csv(PROCESSED / "app_feature_history.csv")
predictions = load_csv(PROCESSED / "predictions.csv")


# --------------------------------------------------
# Sidebar
# --------------------------------------------------

with st.sidebar:
    logo_col, name_col = st.columns([0.8, 2.5], vertical_alignment="center")
    with logo_col:
        st.markdown('<div class="brand-logo-slot"></div>', unsafe_allow_html=True)
    with name_col:
        st.markdown(
            '<div class="brand-name">Market Monitor</div>',
            unsafe_allow_html=True,
        )

    st.divider()
    st.markdown("**Data controls**")

    if st.button("Update market data", type="primary", use_container_width=True):
        try:
            with st.spinner("Updating market data and prediction history..."):
                result = subprocess.run(
                    [sys.executable, str(ROOT / "scripts" / "daily_update.py")],
                    cwd=ROOT,
                    capture_output=True,
                    text=True,
                    timeout=300,
                    check=False,
                )
            st.session_state["update_success"] = result.returncode == 0
            st.session_state["update_log"] = (
                (result.stdout or "") + "\n" + (result.stderr or "")
            ).strip()
        except subprocess.TimeoutExpired:
            st.session_state["update_success"] = False
            st.session_state["update_log"] = "Update timed out after five minutes."
        except Exception as error:
            st.session_state["update_success"] = False
            st.session_state["update_log"] = str(error)
        st.rerun()

    if "update_success" in st.session_state:
        if st.session_state["update_success"]:
            st.success("Update complete.")
        else:
            st.error("Update failed. See log.")
        with st.expander("Update log"):
            st.code(st.session_state.get("update_log", ""), language="text")

    st.divider()
    st.markdown("**Model**")
    st.caption("Random Forest · v1.0.0")
    st.caption("12 features · threshold 0.50")

    st.divider()
    st.markdown("**Sources**")
    st.caption("Yahoo Finance · CBOE")


# --------------------------------------------------
# Page header and market data checks
# --------------------------------------------------

st.title("S&P 500 Market Monitor")

if market.empty:
    st.error("No market price data was found. Use the sidebar update control or run scripts/daily_update.py.")
    st.stop()

required = {"Date", "SP500_Close", "VIX", "NASDAQ"}
missing = required.difference(market.columns)
if missing:
    st.error(f"Market data is missing required columns: {', '.join(sorted(missing))}")
    st.stop()

market = (
    market.dropna(subset=["Date"])
    .sort_values("Date")
    .drop_duplicates("Date", keep="last")
    .reset_index(drop=True)
)
if market.empty:
    st.error("The market data file does not contain valid dates.")
    st.stop()

latest_market = market.iloc[-1]
market_date = latest_market["Date"]
current_close = pd.to_numeric(latest_market["SP500_Close"], errors="coerce")
daily_change = None
if len(market) > 1:
    previous_close = pd.to_numeric(market.iloc[-2]["SP500_Close"], errors="coerce")
    if pd.notna(current_close) and pd.notna(previous_close) and previous_close > 0:
        daily_change = (current_close / previous_close - 1) * 100

put_call_date = None
put_call_value = None
if not put_call.empty and {"Date", "Put_Call_Ratio"}.issubset(put_call.columns):
    put_call = (
        put_call.dropna(subset=["Date"])
        .sort_values("Date")
        .drop_duplicates("Date", keep="last")
        .reset_index(drop=True)
    )
    if not put_call.empty:
        put_call_date = put_call.iloc[-1]["Date"]
        put_call_value = pd.to_numeric(put_call.iloc[-1]["Put_Call_Ratio"], errors="coerce")


# --------------------------------------------------
# Market overview
# --------------------------------------------------

st.divider()
st.subheader("Market overview")

c1, c2, c3, c4 = st.columns(4)
c1.metric("S&P 500", fmt(current_close), f"{daily_change:+.2f}%" if daily_change is not None else None)
c2.metric("VIX", fmt(latest_market["VIX"]))
c3.metric("NASDAQ Composite", fmt(latest_market["NASDAQ"]))
c4.metric("Put/Call ratio", fmt(put_call_value, 4), help="Latest available CBOE SPX options put volume divided by call volume.")

st.caption(f"Prices: {fmt_date(market_date)}  ·  Put/Call: {fmt_date(put_call_date)}")
if put_call_date is None or pd.Timestamp(put_call_date).normalize() < pd.Timestamp(market_date).normalize():
    st.caption("Waiting for the latest CBOE data before generating a new prediction.")


# --------------------------------------------------
# Latest prediction
# --------------------------------------------------

st.divider()
st.subheader("Next session")

if not predictions.empty and "prediction_date" in predictions.columns:
    predictions = predictions.copy()
    predictions["prediction_date"] = pd.to_datetime(predictions["prediction_date"], errors="coerce")
    predictions = predictions.dropna(subset=["prediction_date"]).sort_values("prediction_date")

if not predictions.empty:
    latest_prediction = predictions.iloc[-1]
    prediction_date = latest_prediction["prediction_date"]
    direction = str(latest_prediction.get("predicted_direction", "Unavailable"))
    status = str(latest_prediction.get("status", "UNKNOWN")).upper()

    left, middle, right = st.columns([1.35, 1, 1])
    with left:
        st.caption("DIRECTION")
        st.success("UP") if direction == "UP" else st.error("DOWN / FLAT")
        st.caption(f"Based on {fmt_date(prediction_date)}")
    with middle:
        up_score = pd.to_numeric(latest_prediction.get("up_score"), errors="coerce")
        st.metric("UP score", f"{up_score:.1%}" if pd.notna(up_score) else "N/A")
    with right:
        down_score = pd.to_numeric(latest_prediction.get("down_score"), errors="coerce")
        st.metric("DOWN / FLAT score", f"{down_score:.1%}" if pd.notna(down_score) else "N/A")

    if status == "PENDING":
        st.info("Awaiting the next market close.")
    elif status == "EVALUATED":
        correct = str(latest_prediction.get("correct", "")).strip().lower()
        if correct == "true":
            st.success("The most recent prediction was correct.")
        elif correct == "false":
            st.warning("The most recent prediction was incorrect.")
        else:
            st.caption("The latest prediction is evaluated; correctness is unavailable.")
    st.caption("Scores are not calibrated probabilities.")
else:
    left, right = st.columns([1.25, 1])
    with left:
        st.markdown("**No prediction yet**")
        st.caption("A prediction appears when all required data is available.")
        if not features.empty and "Date" in features.columns:
            st.metric("Latest complete feature date", fmt_date(features["Date"].max()))
    with right:
        st.markdown("**Data status**")
        st.metric("Market date", fmt_date(market_date))
        st.metric("Put/Call date", fmt_date(put_call_date))
        if put_call_date is not None and pd.Timestamp(put_call_date).normalize() < pd.Timestamp(market_date).normalize():
            st.caption("Waiting for matching Put/Call data.")


# --------------------------------------------------
# Historical market data
# --------------------------------------------------

st.divider()
st.subheader("Market history")

if not features.empty and "Date" in features.columns:
    chart_data_all = features.copy()
    chart_data_all["Date"] = pd.to_datetime(chart_data_all["Date"], errors="coerce")
    chart_data_all = chart_data_all.dropna(subset=["Date"]).sort_values("Date")

    if not chart_data_all.empty:
        periods = ["1W", "1M", "3M", "6M", "YTD", "1Y", "All"]
        if "market_history_period" not in st.session_state:
            st.session_state["market_history_period"] = "1M"

        selected_period = st.session_state["market_history_period"]
        range_columns = st.columns(len(periods), gap="small")
        for range_col, period in zip(range_columns, periods):
            with range_col:
                if st.button(
                    period,
                    key=f"market_range_{period}",
                    type="primary" if selected_period == period else "secondary",
                    use_container_width=True,
                ):
                    st.session_state["market_history_period"] = period
                    st.rerun()

        selected_period = st.session_state["market_history_period"]

        last_date = chart_data_all["Date"].max()
        days = {"1W": 7, "1M": 30, "3M": 90, "6M": 180, "1Y": 365}
        if selected_period == "All":
            first_date = chart_data_all["Date"].min()
        elif selected_period == "YTD":
            first_date = pd.Timestamp(last_date.year, 1, 1)
        else:
            first_date = last_date - pd.Timedelta(days=days[selected_period])

        chart_data = chart_data_all[
            (chart_data_all["Date"] >= first_date) & (chart_data_all["Date"] <= last_date)
        ].copy()

        st.caption(f"{len(chart_data):,} sessions  ·  {fmt_date(first_date)} – {fmt_date(last_date)}")

        if chart_data.empty:
            st.info("No observations are available for this period.")
        else:
            chart_start = first_date
            chart_end = last_date
            colors = {"sp500": "#29445B", "vix": "#527A9B", "pcr": "#7FA6C8"}

            chart_left, chart_right = st.columns(2)
            with chart_left:
                st.markdown("**S&P 500 close**")
                if "Close" in chart_data.columns:
                    fig = add_line_chart(chart_data, "Close", "S&P 500", "Index level", colors["sp500"], "Close: %{y:,.2f}", date_start=chart_start, date_end=chart_end)
                    st.plotly_chart(fig, use_container_width=True, theme="streamlit")
                else:
                    st.info("S&P 500 closing data is unavailable.")

            with chart_right:
                st.markdown("**VIX**")
                if "VIX" in chart_data.columns:
                    fig = add_line_chart(chart_data, "VIX", "VIX", "VIX", colors["vix"], "VIX: %{y:.2f}", date_start=chart_start, date_end=chart_end)
                    st.plotly_chart(fig, use_container_width=True, theme="streamlit")
                else:
                    st.info("VIX data is unavailable.")

            st.markdown("**Put/Call ratio**")
            if "Put_Call_Ratio" in chart_data.columns:
                fig = add_line_chart(chart_data, "Put_Call_Ratio", "Put/Call ratio", "Put/Call ratio", colors["pcr"], "Put/Call: %{y:.4f}", height=300, date_start=chart_start, date_end=chart_end, reference_line=True)
                st.plotly_chart(fig, use_container_width=True, theme="streamlit")
            else:
                st.info("Put/Call ratio history is unavailable.")
else:
    st.info("Historical feature data is not available yet.")


# --------------------------------------------------
# Prediction performance
# --------------------------------------------------

st.divider()
st.subheader("Performance")

if not predictions.empty and "status" in predictions.columns:
    status = predictions["status"].astype(str).str.upper()
    evaluated = predictions[status == "EVALUATED"].copy()
    pending = int((status == "PENDING").sum())

    total_col, evaluated_col, pending_col, accuracy_col = st.columns(4)
    total_col.metric("Total predictions", len(predictions))
    evaluated_col.metric("Evaluated", len(evaluated))
    pending_col.metric("Pending", pending)

    if not evaluated.empty:
        if "correct" in evaluated.columns:
            correct = parse_bool(evaluated["correct"]).dropna()
        else:
            correct = pd.Series(dtype=bool)

        accuracy = float(correct.mean()) if not correct.empty else None
        accuracy_col.metric("Live accuracy", f"{accuracy:.1%}" if accuracy is not None else "N/A")

        if {"actual_direction", "predicted_direction"}.issubset(evaluated.columns):
            evaluated["actual_label"] = evaluated["actual_direction"].apply(normalize_direction)
            evaluated["predicted_label"] = evaluated["predicted_direction"].apply(normalize_direction)
            valid = evaluated.dropna(subset=["actual_label", "predicted_label"])
        else:
            valid = pd.DataFrame()

        if not valid.empty:
            labels = ["UP", "DOWN / FLAT"]
            matrix = pd.crosstab(valid["actual_label"], valid["predicted_label"]).reindex(index=labels, columns=labels, fill_value=0)
            up_total = matrix.loc["UP"].sum()
            down_total = matrix.loc["DOWN / FLAT"].sum()
            up_recall = matrix.loc["UP", "UP"] / up_total if up_total else None
            down_recall = matrix.loc["DOWN / FLAT", "DOWN / FLAT"] / down_total if down_total else None
            balanced = (up_recall + down_recall) / 2 if up_recall is not None and down_recall is not None else None
            baseline = up_total / len(valid)

            st.markdown("#### By direction")
            a, b, c = st.columns(3)
            a.metric("Balanced accuracy", f"{balanced:.1%}" if balanced is not None else "N/A")
            b.metric("UP recall", f"{up_recall:.1%}" if up_recall is not None else "N/A")
            c.metric("DOWN / FLAT recall", f"{down_recall:.1%}" if down_recall is not None else "N/A")

            if accuracy is not None:
                st.markdown("#### Baseline")
                st.metric("Always-UP baseline", f"{baseline:.1%}", delta=f"{accuracy - baseline:+.1%}")

            st.markdown("#### Confusion matrix")
            st.caption("Rows: actual · Columns: predicted")
            st.dataframe(matrix.rename_axis("Actual direction"), use_container_width=True)

        st.markdown("#### Recent results")
        columns = [c for c in ["prediction_date", "predicted_direction", "actual_direction", "actual_return", "correct"] if c in evaluated.columns]
        recent = evaluated[columns].copy()
        if "prediction_date" in recent.columns:
            recent["prediction_date"] = pd.to_datetime(recent["prediction_date"], errors="coerce")
            recent = recent.sort_values("prediction_date", ascending=False)
        st.dataframe(recent.head(10), use_container_width=True, hide_index=True)
    else:
        accuracy_col.metric("Live accuracy", "—")
        st.caption("Live results appear after the next market session is evaluated.")
else:
    st.caption("No predictions recorded yet.")


# --------------------------------------------------
# Raw data tables
# --------------------------------------------------

st.divider()
with st.expander("Market data"):
    st.dataframe(market.sort_values("Date", ascending=False).head(10), use_container_width=True, hide_index=True)

with st.expander("Put/Call data"):
    if not put_call.empty:
        st.dataframe(put_call.sort_values("Date", ascending=False).head(10), use_container_width=True, hide_index=True)
    else:
        st.caption("No Put/Call data available.")

st.divider()

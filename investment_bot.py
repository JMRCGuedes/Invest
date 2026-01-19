import yfinance as yf
import pandas as pd
from datetime import datetime
import json
import os

# =========================================================
# CONFIGURATION
# =========================================================
INITIAL_CAPITAL = 10_000
RISK_PER_TRADE = 0.02
BACKTEST_LOOKAHEAD_DAYS = 5
TRADE_CONFIDENCE_THRESHOLD = 30
BROKER_FEE_PERCENT = 0.001  # 0.1% per trade

STATE_FILE = "state.json"
TRADE_HISTORY_FILE = "trade_history.csv"
DAILY_SIGNALS_FILE = "daily_signals.csv"
PORTFOLIO_DETAILS_FILE = "portfolio_details.csv"
PORTFOLIO_SUMMARY_FILE = "portfolio_summary.csv"

# =========================================================
# REVOLUT SETTINGS
# =========================================================
BROKER = "REVOLUT"
ALLOW_FRACTIONAL_STOCKS = True
ALLOW_FRACTIONAL_ETFS = False
MIN_STOCK_FRACTION = 0.01

# =========================================================
# ASSETS
# =========================================================
STOCKS = [
    "AAPL","MSFT","NVDA","AMZN","GOOGL","GOOG","TSLA","META",
    "ADBE","AMD","INTC","CSCO","QCOM","CRM","AVGO","ORCL",
    "IBM","TXN","AMGN","HON","PEP","KO","MCD","WMT","CAT",
    "JNJ","V","HD","BAC","JPM","UNH","CVX","XOM","NFLX",
    "LMT","BLK","SPGI","MS","RTX"
]

ETFS = [
    "SPY","VOO","IVV","VTI","QQQ","VUG","VEA","VTV","IEFA",
    "AGG","IEMG","IJH","IJR","VIG","VYM","SCHD","XLK","VT","ACWI"
]

ALL_ASSETS = STOCKS + ETFS

# =========================================================
# INDICATORS
# =========================================================
def exponential_moving_average(series, period):
    return series.ewm(span=period, adjust=False).mean()

def relative_strength_index(series, period=14):
    delta = series.diff()
    gains = delta.clip(lower=0)
    losses = -delta.clip(upper=0)
    rs = gains.ewm(period).mean() / losses.ewm(period).mean()
    return 100 - (100 / (1 + rs))

def macd_indicator(series):
    macd_line = exponential_moving_average(series, 12) - exponential_moving_average(series, 26)
    signal_line = exponential_moving_average(macd_line, 9)
    return macd_line, signal_line

# =========================================================
# BACKTESTING
# =========================================================
def run_backtest(df):
    buy_wins = buy_total = sell_wins = sell_total = 0

    for i in range(len(df) - BACKTEST_LOOKAHEAD_DAYS):
        current = df.iloc[i]
        future = df.iloc[i + BACKTEST_LOOKAHEAD_DAYS]

        # Skip if NaN
        if pd.isna(current["RSI"]) or pd.isna(current["EMA20"]) or pd.isna(current["EMA50"]) or pd.isna(current["MACD"]):
            continue

        buy_score = 0
        sell_score = 0

        if current["RSI"] < 30:
            buy_score += 25
        if current["RSI"] > 70:
            sell_score += 25

        if current["EMA20"] > current["EMA50"]:
            buy_score += 25
        else:
            sell_score += 25

        if current["MACD"] > current["MACD_SIGNAL"]:
            buy_score += 25
        else:
            sell_score += 25

        if buy_score > sell_score:
            buy_total += 1
            if future["Close"] > current["Close"]:
                buy_wins += 1
        elif sell_score > buy_score:
            sell_total += 1
            if future["Close"] < current["Close"]:
                sell_wins += 1

    buy_accuracy = buy_wins / buy_total if buy_total else 0.5
    sell_accuracy = sell_wins / sell_total if sell_total else 0.5

    return buy_accuracy, sell_accuracy

# =========================================================
# LOAD STATE
# =========================================================
if os.path.exists(STATE_FILE):
    with open(STATE_FILE, "r") as file:
        state = json.load(file)
        available_cash = state["available_cash"]
        portfolio = state["portfolio"]
else:
    available_cash = INITIAL_CAPITAL
    portfolio = {asset: {"quantity": 0, "average_price": 0} for asset in ALL_ASSETS}

trade_log = []

# =========================================================
# MAIN LOOP
# =========================================================
for asset in ALL_ASSETS:
    print(f"Processing {asset}")
    try:
        df = yf.download(asset, period="6mo", progress=False, auto_adjust=False)

        # Fix MultiIndex columns
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        if df.empty or "Close" not in df.columns or len(df) < 60:
            print(f"Skipping {asset}: insufficient data")
            continue

        df["EMA20"] = exponential_moving_average(df["Close"], 20)
        df["EMA50"] = exponential_moving_average(df["Close"], 50)
        df["RSI"] = relative_strength_index(df["Close"])
        df["MACD"], df["MACD_SIGNAL"] = macd_indicator(df["Close"])

        buy_acc, sell_acc = run_backtest(df)

        latest = df.iloc[-1]

        latest_rsi = latest["RSI"]
        latest_ema20 = latest["EMA20"]
        latest_ema50 = latest["EMA50"]
        latest_macd = latest["MACD"]
        latest_macd_signal = latest["MACD_SIGNAL"]

        if pd.isna(latest_rsi) or pd.isna(latest_ema20) or pd.isna(latest_ema50) or pd.isna(latest_macd):
            print(f"Skipping {asset}: NaN indicators")
            continue

        buy_conf = 0
        sell_conf = 0

        if latest_rsi < 30:
            buy_conf += 25
        if latest_rsi > 70:
            sell_conf += 25

        if latest_ema20 > latest_ema50:
            buy_conf += 25
        else:
            sell_conf += 25

        if latest_macd > latest_macd_signal:
            buy_conf += 25
        else:
            sell_conf += 25

        buy_conf *= buy_acc
        sell_conf *= sell_acc

        if buy_conf > sell_conf:
            decision = "BUY"
            confidence_score = int(buy_conf)
        elif sell_conf > buy_conf:
            decision = "SELL"
            confidence_score = int(sell_conf)
        else:
            decision = "HOLD"
            confidence_score = 0

        position = portfolio[asset]
        current_price = float(latest["Close"])

        # =====================================================
        # EXECUTE TRADE (REVOLUT FRACTIONS + FEES)
        # =====================================================
        if decision == "BUY" and confidence_score >= TRADE_CONFIDENCE_THRESHOLD:
            max_risk_amount = available_cash * RISK_PER_TRADE

            is_stock = asset in STOCKS
            allow_fractional = ALLOW_FRACTIONAL_STOCKS if is_stock else ALLOW_FRACTIONAL_ETFS

            if allow_fractional:
                quantity_to_buy = max_risk_amount / current_price
                quantity_to_buy = round(quantity_to_buy, 2)
                if quantity_to_buy < MIN_STOCK_FRACTION:
                    quantity_to_buy = 0
            else:
                quantity_to_buy = int(max_risk_amount // current_price)

            total_cost = quantity_to_buy * current_price
            total_cost += total_cost * BROKER_FEE_PERCENT  # apply broker fee

            if quantity_to_buy > 0 and total_cost <= available_cash:
                available_cash -= total_cost
                new_quantity = position["quantity"] + quantity_to_buy
                new_average_price = (
                    (position["quantity"] * position["average_price"] + total_cost)
                    / new_quantity
                )
                portfolio[asset] = {
                    "quantity": round(new_quantity, 4),
                    "average_price": round(new_average_price, 2)
                }

        elif decision == "SELL" and position["quantity"] > 0:
            total_value = position["quantity"] * current_price
            total_value -= total_value * BROKER_FEE_PERCENT  # apply fee
            available_cash += total_value
            portfolio[asset] = {"quantity": 0, "average_price": 0}

        # =====================================================
        # LOG TRADE
        # =====================================================
        trade_log.append({
            "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "asset": asset,
            "asset_type": "Stock" if asset in STOCKS else "ETF",
            "decision": decision,
            "confidence": confidence_score,
            "price": round(current_price, 2)
        })

        print(asset, decision, confidence_score)

    except Exception as error:
        print(f"❌ Error processing {asset}: {error}")

# =========================================================
# SAVE STATE
# =========================================================
with open(STATE_FILE, "w") as file:
    json.dump({
        "available_cash": round(available_cash, 2),
        "portfolio": portfolio
    }, file, indent=2)

# =========================================================
# SAVE REPORTS
# =========================================================
df_trades = pd.DataFrame(trade_log)
df_trades.to_csv(DAILY_SIGNALS_FILE, index=False)

if os.path.exists(TRADE_HISTORY_FILE):
    df_trades.to_csv(TRADE_HISTORY_FILE, mode="a", index=False, header=False)
else:
    df_trades.to_csv(TRADE_HISTORY_FILE, index=False)

# =========================================================
# PORTFOLIO PERFORMANCE
# =========================================================
portfolio_rows = []
total_invested = 0
total_current_value = 0

for asset, pos in portfolio.items():
    if pos["quantity"] == 0:
        continue

    price = float(yf.download(asset, period="1d", progress=False)["Close"].iloc[-1])
    invested_value = pos["quantity"] * pos["average_price"]
    current_value = pos["quantity"] * price
    profit = current_value - invested_value

    total_invested += invested_value
    total_current_value += current_value

    portfolio_rows.append({
        "asset": asset,
        "type": "Stock" if asset in STOCKS else "ETF",
        "quantity": pos["quantity"],
        "average_price": pos["average_price"],
        "current_price": round(price, 2),
        "invested_value": round(invested_value, 2),
        "current_value": round(current_value, 2),
        "profit": round(profit, 2),
        "return_pct": round((profit / invested_value) * 100, 2)
    })

pd.DataFrame(portfolio_rows).to_csv(PORTFOLIO_DETAILS_FILE, index=False)

summary = {
    "available_cash": round(available_cash, 2),
    "total_invested": round(total_invested, 2),
    "portfolio_value": round(available_cash + total_current_value, 2),
    "total_profit": round(available_cash + total_current_value - INITIAL_CAPITAL, 2)
}

pd.DataFrame([summary]).to_csv(PORTFOLIO_SUMMARY_FILE, index=False)

print("✅ Revolut Investment Bot finished successfully")

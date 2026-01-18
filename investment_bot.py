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

STATE_FILE = "state.json"
HISTORY_FILE = "trade_history.csv"
DAILY_REPORT_FILE = "daily_signals.csv"
PORTFOLIO_DETAIL_FILE = "portfolio_details.csv"
PORTFOLIO_SUMMARY_FILE = "portfolio_summary.csv"

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

def bollinger_bands(series, period=20):
    moving_average = series.rolling(period).mean()
    standard_deviation = series.rolling(period).std()
    upper_band = moving_average + 2 * standard_deviation
    lower_band = moving_average - 2 * standard_deviation
    return upper_band, lower_band

# =========================================================
# BACKTESTING
# =========================================================
def run_backtest(dataframe):
    buy_wins = buy_total = sell_wins = sell_total = 0

    for index in range(len(dataframe) - BACKTEST_LOOKAHEAD_DAYS):
        current = dataframe.iloc[index]
        future = dataframe.iloc[index + BACKTEST_LOOKAHEAD_DAYS]

        buy_score = sell_score = 0

        if current.RSI < 30: buy_score += 25
        if current.RSI > 70: sell_score += 25
        buy_score += 25 if current.EMA20 > current.EMA50 else 0
        sell_score += 25 if current.EMA20 <= current.EMA50 else 0
        buy_score += 25 if current.MACD > current.MACD_SIGNAL else 0
        sell_score += 25 if current.MACD <= current.MACD_SIGNAL else 0

        if buy_score > sell_score:
            buy_total += 1
            if future.Close > current.Close:
                buy_wins += 1
        elif sell_score > buy_score:
            sell_total += 1
            if future.Close < current.Close:
                sell_wins += 1

    buy_accuracy = buy_wins / buy_total if buy_total else 0.5
    sell_accuracy = sell_wins / sell_total if sell_total else 0.5

    return buy_accuracy, sell_accuracy

# =========================================================
# LOAD OR INITIALIZE STATE
# =========================================================
if os.path.exists(STATE_FILE):
    with open(STATE_FILE, "r") as file:
        state = json.load(file)
        available_cash = state["available_cash"]
        portfolio = state["portfolio"]
else:
    available_cash = INITIAL_CAPITAL
    portfolio = {
        asset: {"quantity": 0, "average_price": 0}
        for asset in ALL_ASSETS
    }

trade_log = []

# =========================================================
# MAIN EXECUTION
# =========================================================
for asset in ALL_ASSETS:
    try:
        price_data = yf.download(asset, period="6mo", progress=False)
        if price_data.empty:
            continue

        price_data["EMA20"] = exponential_moving_average(price_data.Close, 20)
        price_data["EMA50"] = exponential_moving_average(price_data.Close, 50)
        price_data["RSI"] = relative_strength_index(price_data.Close)
        price_data["MACD"], price_data["MACD_SIGNAL"] = macd_indicator(price_data.Close)
        price_data["BB_UPPER"], price_data["BB_LOWER"] = bollinger_bands(price_data.Close)

        buy_accuracy, sell_accuracy = run_backtest(price_data)
        latest = price_data.iloc[-1]
        current_price = float(latest.Close)

        buy_confidence = sell_confidence = 0

        if latest.RSI < 30: buy_confidence += 25
        if latest.RSI > 70: sell_confidence += 25
        buy_confidence += 25 if latest.EMA20 > latest.EMA50 else 0
        sell_confidence += 25 if latest.EMA20 <= latest.EMA50 else 0
        buy_confidence += 25 if latest.MACD > latest.MACD_SIGNAL else 0
        sell_confidence += 25 if latest.MACD <= latest.MACD_SIGNAL else 0

        buy_confidence *= buy_accuracy
        sell_confidence *= sell_accuracy

        if buy_confidence > sell_confidence:
            decision = "BUY"
            confidence_score = int(buy_confidence)
        elif sell_confidence > buy_confidence:
            decision = "SELL"
            confidence_score = int(sell_confidence)
        else:
            decision = "HOLD"
            confidence_score = 0

        position = portfolio[asset]

        if decision == "BUY":
            max_risk_amount = available_cash * RISK_PER_TRADE
            quantity_to_buy = int(max_risk_amount // current_price)

            if quantity_to_buy > 0:
                total_cost = quantity_to_buy * current_price
                available_cash -= total_cost

                new_quantity = position["quantity"] + quantity_to_buy
                new_average_price = (
                    (position["quantity"] * position["average_price"] + total_cost)
                    / new_quantity
                )

                portfolio[asset] = {
                    "quantity": new_quantity,
                    "average_price": round(new_average_price, 2)
                }

        elif decision == "SELL" and position["quantity"] > 0:
            available_cash += position["quantity"] * current_price
            portfolio[asset] = {"quantity": 0, "average_price": 0}

        trade_log.append({
            "date": datetime.now(),
            "asset": asset,
            "asset_type": "Stock" if asset in STOCKS else "ETF",
            "decision": decision,
            "confidence": confidence_score
        })

    except Exception:
        continue

# =========================================================
# SAVE STATE & REPORTS
# =========================================================
with open(STATE_FILE, "w") as file:
    json.dump({
        "available_cash": available_cash,
        "portfolio": portfolio
    }, file, indent=2)

pd.DataFrame(trade_log)\
    .sort_values("confidence", ascending=False)\
    .to_csv(DAILY_REPORT_FILE, index=False)

# =========================================================
# PORTFOLIO PERFORMANCE
# =========================================================
portfolio_rows = []
total_invested = 0
total_current_value = 0

for asset, position in portfolio.items():
    if position["quantity"] == 0:
        continue

    current_price = float(
        yf.download(asset, period="1d", progress=False).Close.iloc[-1]
    )

    invested_value = position["quantity"] * position["average_price"]
    current_value = position["quantity"] * current_price
    profit = current_value - invested_value

    total_invested += invested_value
    total_current_value += current_value

    portfolio_rows.append({
        "asset": asset,
        "type": "Stock" if asset in STOCKS else "ETF",
        "quantity": position["quantity"],
        "average_price": position["average_price"],
        "current_price": round(current_price, 2),
        "invested_value": round(invested_value, 2),
        "current_value": round(current_value, 2),
        "profit": round(profit, 2),
        "return_percent": round((profit / invested_value) * 100, 2)
    })

pd.DataFrame(portfolio_rows).to_csv(PORTFOLIO_DETAIL_FILE, index=False)

portfolio_summary = {
    "available_cash": round(available_cash, 2),
    "total_invested": round(total_invested, 2),
    "current_invested_value": round(total_current_value, 2),
    "portfolio_value": round(available_cash + total_current_value, 2),
    "total_profit": round(
        available_cash + total_current_value - INITIAL_CAPITAL, 2
    )
}

pd.DataFrame([portfolio_summary]).to_csv(PORTFOLIO_SUMMARY_FILE, index=False)

print("✅ Investment bot executed successfully")

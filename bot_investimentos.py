import yfinance as yf
import pandas as pd
from datetime import datetime
import json
import os

# -------- CONFIGURAÇÃO --------
DINHEIRO_INICIAL = 10000
RISCO_POR_TRADE = 0.02  # 2%

# Top 100 ações global
ACOES = [
    "AAPL","MSFT","NVDA","AMZN","GOOGL","META","TSLA","BRK-B","JNJ","V",
    "PG","UNH","MA","HD","BAC","XOM","PFE","CVX","KO","COST","ABBV","ADBE",
    "CRM","CSCO","PEP","AVGO","LLY","TMUS","ORCL","NKE","ASML","INTC","TMO",
    "MCD","WMT","DHR","ACN","QCOM","AMGN","TXN","MDT","HON","LIN","NEE",
    "UNP","LOW","RTX","PM","UPS","CAT","SBUX","IBM","BLK","AXP","SPGI","MS",
    "GE","LMT","AMT","PLD","CHTR","C","BKNG","TJX","MMM","CVS","GILD","SYK",
    "ZTS","ANTM","MO","DE","FIS","T","VZ","DUK","CCI","SO","BSX","BDX","ETN",
    "CL","EL","SHW","ICE","ADP","APD","ITW","ECL"
]

# Top 20 ETFs populares / maior AUM
ETFS = [
    "SPY","VOO","IVV","VTI","QQQ","VUG","VEA","VTV","IEFA","AGG",
    "IEMG","IJH","IJR","VIG","VYM","SCHD","XLK","SCZ","VT","ACWI"
]

ATIVOS = ACOES + ETFS

ESTADO_FICHEIRO = "estado.json"
HISTORICO_FICHEIRO = "historico_total.csv"

# -------- FUNÇÕES DE INDICADORES --------
def EMA(series, period):
    return series.ewm(span=period, adjust=False).mean()

def RSI(series, period=14):
    delta = series.diff()
    up = delta.clip(lower=0)
    down = -1 * delta.clip(upper=0)
    ema_up = up.ewm(com=period-1, adjust=False).mean()
    ema_down = down.ewm(com=period-1, adjust=False).mean()
    rs = ema_up / ema_down
    return 100 - (100 / (1 + rs))

def MACD(series, fast=12, slow=26, signal=9):
    ema_fast = series.ewm(span=fast, adjust=False).mean()
    ema_slow = series.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    return macd_line, signal_line

def BollingerBands(series, period=20, std_dev=2):
    sma = series.rolling(window=period).mean()
    std = series.rolling(window=period).std()
    upper = sma + std_dev * std
    lower = sma - std_dev * std
    return upper, lower

# -------- CARREGAR ESTADO --------
if os.path.exists(ESTADO_FICHEIRO):
    with open(ESTADO_FICHEIRO, "r") as f:
        estado = json.load(f)
        dinheiro = estado.get("dinheiro", DINHEIRO_INICIAL)
        portfolio = estado.get("portfolio", {ativo: 0 for ativo in ATIVOS})
else:
    dinheiro = DINHEIRO_INICIAL
    portfolio = {ativo: 0 for ativo in ATIVOS}

historico = []

# -------- LOOP PRINCIPAL --------
for ativo in ATIVOS:
    data = yf.download(ativo, period="6mo", interval="1d", progress=False)
    if data.empty or len(data) < 60:
        continue

    # Resolver MultiIndex
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.get_level_values(0)

    # Indicadores
    data["EMA20"] = EMA(data["Close"], 20)
    data["EMA50"] = EMA(data["Close"], 50)
    data["RSI"] = RSI(data["Close"], 14)
    data["MACD"], data["MACD_signal"] = MACD(data["Close"])
    data["BB_upper"], data["BB_lower"] = BollingerBands(data["Close"])

    ultimo = data.iloc[-1]

    rsi = ultimo["RSI"]
    ema20 = ultimo["EMA20"]
    ema50 = ultimo["EMA50"]
    macd = ultimo["MACD"]
    macd_signal = ultimo["MACD_signal"]
    close = float(ultimo["Close"])
    bb_upper = ultimo["BB_upper"]
    bb_lower = ultimo["BB_lower"]

    # -------- CALCULAR CONFIANÇA --------
    conf_buy = 0
    conf_sell = 0

    # RSI
    if not pd.isna(rsi):
        if rsi < 30:
            conf_buy += (30 - rsi) / 30 * 25
        elif rsi > 70:
            conf_sell += (rsi - 70) / 30 * 25

    # EMA
    if not pd.isna(ema20) and not pd.isna(ema50):
        if ema20 > ema50:
            conf_buy += 25
        else:
            conf_sell += 25

    # MACD
    if not pd.isna(macd) and not pd.isna(macd_signal):
        if macd > macd_signal:
            conf_buy += 25
        else:
            conf_sell += 25

    # Bollinger Bands
    if not pd.isna(bb_upper) and not pd.isna(bb_lower):
        if close < bb_lower:
            conf_buy += 25
        elif close > bb_upper:
            conf_sell += 25

    # -------- DECISÃO FINAL --------
    if conf_buy > conf_sell and conf_buy > 0:
        sinal = "BUY"
        confianca = min(int(conf_buy), 100)
    elif conf_sell > conf_buy and conf_sell > 0:
        sinal = "SELL"
        confianca = min(int(conf_sell), 100)
    else:
        sinal = "HOLD"
        confianca = 0

    # -------- PAPER TRADING --------
    if sinal == "BUY" and dinheiro > 0:
        risco = dinheiro * RISCO_POR_TRADE
        quantidade = int(risco // close)
        if quantidade > 0:
            dinheiro -= quantidade * close
            portfolio[ativo] += quantidade
    elif sinal == "SELL" and portfolio[ativo] > 0:
        dinheiro += portfolio[ativo] * close
        portfolio[ativo] = 0

    # -------- ADICIONAR AO HISTÓRICO --------
    historico.append({
        "Data": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "Ativo": ativo,
        "Preço": round(close, 2),
        "RSI": round(rsi, 2) if not pd.isna(rsi) else None,
        "Sinal": sinal,
        "Confiança": confianca
    })

# -------- SALVAR ESTADO --------
estado = {"dinheiro": dinheiro, "portfolio": portfolio}
with open(ESTADO_FICHEIRO, "w") as f:
    json.dump(estado, f, indent=2)

# -------- SALVAR HISTÓRICO ORDENADO POR CONFIANÇA --------
df = pd.DataFrame(historico)
df_sorted = df.sort_values(by="Confiança", ascending=False)

if os.path.exists(HISTORICO_FICHEIRO):
    historico_antigo = pd.read_csv(HISTORICO_FICHEIRO)
    historico_novo = pd.concat([historico_antigo, df_sorted], ignore_index=True)
else:
    historico_novo = df_sorted

historico_novo.to_csv(HISTORICO_FICHEIRO, index=False)
df_sorted.to_csv("relatorio_diario.csv", index=False)

# -------- PRINT RESUMO --------
print("💰 Dinheiro final:", round(dinheiro, 2))
print("📊 Portfólio (posições abertas):")
for ativo, qtd in portfolio.items():
    if qtd > 0:
        print(f"  {ativo}: {qtd}")

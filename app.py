from flask import Flask, render_template, jsonify, session, redirect, url_for, request, make_response
from functools import wraps
from fpdf import FPDF
import pandas as pd
import json
import os
from datetime import datetime

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'invest-portfolio-secret-key-2026')

# ── Auth ──────────────────────────────────────────────────────────────────────
USERS = {"João Guedes": "admin"}

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'username' not in session:
            return redirect(url_for('login_page'))
        return f(*args, **kwargs)
    return decorated

@app.route('/login', methods=['GET', 'POST'])
def login_page():
    if 'username' in session:
        return redirect(url_for('index'))
    error = None
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        if username in USERS and USERS[username] == password:
            session['username'] = username
            return redirect(url_for('index'))
        error = 'Invalid username or password.'
    return render_template('login.html', error=error)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login_page'))

# ── File paths ────────────────────────────────────────────────────────────────
STATE_FILE             = "state.json"
PORTFOLIO_SUMMARY_FILE = "portfolio_summary.csv"
PORTFOLIO_DETAILS_FILE = "portfolio_details.csv"
DAILY_SIGNALS_FILE     = "daily_signals.csv"
TRADE_HISTORY_FILE     = "trade_history.csv"
INITIAL_CAPITAL        = 10_000

# ── Pages ─────────────────────────────────────────────────────────────────────
@app.route('/')
@login_required
def index():
    return render_template('index.html', username=session['username'])

@app.route('/details')
@login_required
def details():
    return render_template('details.html', username=session['username'])

@app.route('/notifications')
@login_required
def notifications():
    return render_template('notifications.html', username=session['username'])

# ── API ───────────────────────────────────────────────────────────────────────
@app.route('/api/summary')
@login_required
def get_summary():
    try:
        if os.path.exists(PORTFOLIO_SUMMARY_FILE):
            df = pd.read_csv(PORTFOLIO_SUMMARY_FILE)
            return jsonify(df.to_dict('records')[0])
        return jsonify({"error": "Summary file not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/portfolio')
@login_required
def get_portfolio():
    try:
        if os.path.exists(PORTFOLIO_DETAILS_FILE):
            df = pd.read_csv(PORTFOLIO_DETAILS_FILE)
            return jsonify(df.to_dict('records'))
        return jsonify([])
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/signals')
@login_required
def get_signals():
    try:
        if os.path.exists(DAILY_SIGNALS_FILE):
            df = pd.read_csv(DAILY_SIGNALS_FILE)
            return jsonify(df.to_dict('records'))
        return jsonify([])
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/trade-history')
@login_required
def get_trade_history():
    try:
        if os.path.exists(TRADE_HISTORY_FILE):
            df = pd.read_csv(TRADE_HISTORY_FILE).dropna(subset=['price'])
            return jsonify(df.tail(100).to_dict('records'))
        return jsonify([])
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/assets')
@login_required
def get_assets():
    try:
        if not os.path.exists(TRADE_HISTORY_FILE):
            return jsonify([])
        df = pd.read_csv(TRADE_HISTORY_FILE).dropna(subset=['price'])
        return jsonify(sorted(df['asset'].unique().tolist()))
    except Exception as e:
        return jsonify([])

@app.route('/api/asset-performance/<asset>')
@login_required
def get_asset_performance(asset):
    try:
        if not os.path.exists(TRADE_HISTORY_FILE):
            return jsonify([])
        df = pd.read_csv(TRADE_HISTORY_FILE).dropna(subset=['price'])
        df = df[df['asset'] == asset].copy()
        if df.empty:
            return jsonify([])
        df['date_dt'] = pd.to_datetime(df['date'])
        df = df.sort_values('date_dt')
        position = 0
        total_cost = 0
        cumulative_profit = 0
        results = []
        for _, row in df.iterrows():
            decision = row['decision']
            price = float(row['price'])
            date = row['date_dt'].strftime('%Y-%m-%d')
            if decision == 'BUY' and position == 0:
                position = 1
                total_cost = price
                results.append({'date': date, 'decision': 'BUY', 'price': price,
                                 'cumulative_profit': round(cumulative_profit, 2), 'position_value': round(price, 2)})
            elif decision == 'SELL' and position > 0:
                cumulative_profit += price - total_cost
                position = 0
                total_cost = 0
                results.append({'date': date, 'decision': 'SELL', 'price': price,
                                 'cumulative_profit': round(cumulative_profit, 2), 'position_value': 0})
            elif position > 0:
                results.append({'date': date, 'decision': decision, 'price': price,
                                 'cumulative_profit': round(cumulative_profit, 2), 'position_value': round(price, 2)})
        return jsonify(results[-50:] if len(results) > 50 else results)
    except Exception as e:
        return jsonify([])

@app.route('/api/asset-history/<asset>')
@login_required
def get_asset_history(asset):
    try:
        if not os.path.exists(TRADE_HISTORY_FILE):
            return jsonify([])
        df = pd.read_csv(TRADE_HISTORY_FILE)
        df = df[df['asset'] == asset]
        if df.empty:
            return jsonify([])
        df['date_only'] = pd.to_datetime(df['date']).dt.date
        df = df.sort_values('date_only')
        daily_data = {}
        for _, row in df.iterrows():
            daily_data[row['date_only']] = {
                'date': str(row['date_only']),
                'decision': row['decision'],
                'confidence': int(row['confidence']),
                'price': float(row['price'])
            }
        result = list(daily_data.values())
        return jsonify(result[-30:] if len(result) > 30 else result)
    except Exception as e:
        return jsonify([])

@app.route('/api/asset-allocation')
@login_required
def get_asset_allocation():
    try:
        if os.path.exists(PORTFOLIO_DETAILS_FILE):
            df = pd.read_csv(PORTFOLIO_DETAILS_FILE)
            return jsonify(df[['asset', 'current_value']].to_dict('records'))
        return jsonify([])
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/asset-stats')
@login_required
def get_asset_stats():
    try:
        if not os.path.exists(TRADE_HISTORY_FILE):
            return jsonify({"hold_time": [], "profitability": []})
        df = pd.read_csv(TRADE_HISTORY_FILE).dropna(subset=['price'])
        df['date_dt'] = pd.to_datetime(df['date'])
        df = df.sort_values('date_dt')
        hold_days = {}
        profit_pct = {}
        for asset in df['asset'].unique():
            asset_df = df[df['asset'] == asset].sort_values('date_dt')
            buy_price = None
            buy_date = None
            total_days = 0
            total_profit = 0.0
            num_closed = 0
            for _, row in asset_df.iterrows():
                if row['decision'] == 'BUY' and buy_price is None:
                    buy_price = float(row['price'])
                    buy_date = row['date_dt']
                elif row['decision'] == 'SELL' and buy_price is not None:
                    total_days += (row['date_dt'] - buy_date).days
                    total_profit += (float(row['price']) - buy_price) / buy_price * 100
                    num_closed += 1
                    buy_price = None
                    buy_date = None
            if total_days > 0:
                hold_days[asset] = total_days
            if num_closed > 0:
                profit_pct[asset] = round(total_profit, 2)
        hold_time = sorted(
            [{"asset": k, "days_held": v} for k, v in hold_days.items()],
            key=lambda x: x["days_held"], reverse=True)[:10]
        profitability = sorted(
            [{"asset": k, "total_return_pct": v} for k, v in profit_pct.items()],
            key=lambda x: x["total_return_pct"], reverse=True)[:10]
        return jsonify({"hold_time": hold_time, "profitability": profitability})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/notifications')
@login_required
def get_notifications():
    """Recent BUY/SELL actions from the last bot run for the notifications panel."""
    try:
        items = []
        if os.path.exists(DAILY_SIGNALS_FILE):
            df = pd.read_csv(DAILY_SIGNALS_FILE)
            actions = df[df['decision'].isin(['BUY', 'SELL'])]
            for _, row in actions.iterrows():
                items.append({
                    'type': row['decision'],
                    'asset': row['asset'],
                    'price': float(row['price']),
                    'confidence': int(row['confidence']),
                    'date': row['date'],
                })
        return jsonify(items)
    except Exception as e:
        return jsonify([])

# ── PDF Report ────────────────────────────────────────────────────────────────
def _col(value, pos='16,163,74', neg='220,38,38'):
    return pos if value >= 0 else neg

def generate_pdf():
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_margins(15, 15, 15)

    # ── Header ────────────────────────────────────────
    pdf.set_fill_color(102, 126, 234)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font('Helvetica', 'B', 18)
    pdf.cell(0, 14, 'Investment Portfolio Report', fill=True, align='C', new_x='LMARGIN', new_y='NEXT')
    pdf.set_font('Helvetica', '', 10)
    pdf.cell(0, 8, f'Generated on {datetime.now().strftime("%Y-%m-%d %H:%M")}', fill=True, align='C', new_x='LMARGIN', new_y='NEXT')
    pdf.set_text_color(0, 0, 0)
    pdf.ln(6)

    # ── Portfolio Summary ──────────────────────────────
    if os.path.exists(PORTFOLIO_SUMMARY_FILE):
        s = pd.read_csv(PORTFOLIO_SUMMARY_FILE).iloc[0]
        profit    = float(s['total_profit'])
        profit_pct = profit / INITIAL_CAPITAL * 100
        sign      = '+' if profit >= 0 else ''
        r, g, b   = (16, 163, 74) if profit >= 0 else (220, 38, 38)

        pdf.set_font('Helvetica', 'B', 13)
        pdf.set_fill_color(241, 245, 249)
        pdf.cell(0, 9, 'Portfolio Summary', fill=True, new_x='LMARGIN', new_y='NEXT')
        pdf.ln(2)

        col_w = (pdf.w - 30) / 3
        pdf.set_font('Helvetica', '', 9)
        pdf.set_fill_color(248, 250, 252)
        for label, value in [
            ('Available Cash',   f"${float(s['available_cash']):,.2f}"),
            ('Portfolio Value',  f"${float(s['portfolio_value']):,.2f}"),
            ('Total Invested',   f"${float(s['total_invested']):,.2f}"),
        ]:
            pdf.set_fill_color(248, 250, 252)
            pdf.set_text_color(100, 116, 139)
            pdf.cell(col_w, 7, label, border=1, fill=True, align='C')
        pdf.ln()
        pdf.set_text_color(30, 41, 59)
        pdf.set_font('Helvetica', 'B', 11)
        for value in [f"${float(s['available_cash']):,.2f}", f"${float(s['portfolio_value']):,.2f}", f"${float(s['total_invested']):,.2f}"]:
            pdf.cell(col_w, 9, value, border=1, align='C')
        pdf.ln(12)

        pdf.set_font('Helvetica', 'B', 12)
        pdf.set_text_color(r, g, b)
        pdf.cell(0, 8, f'Total P/L: {sign}${profit:,.2f}  ({sign}{profit_pct:.2f}%)', align='C', new_x='LMARGIN', new_y='NEXT')
        pdf.set_text_color(0, 0, 0)
        pdf.ln(6)

    # ── Signal Summary ─────────────────────────────────
    if os.path.exists(DAILY_SIGNALS_FILE):
        df     = pd.read_csv(DAILY_SIGNALS_FILE)
        n_buy  = int((df['decision'] == 'BUY').sum())
        n_sell = int((df['decision'] == 'SELL').sum())
        n_hold = int((df['decision'] == 'HOLD').sum())

        pdf.set_font('Helvetica', 'B', 13)
        pdf.set_fill_color(241, 245, 249)
        pdf.cell(0, 9, 'Signal Summary', fill=True, new_x='LMARGIN', new_y='NEXT')
        pdf.ln(2)

        col_w = (pdf.w - 30) / 3
        pdf.set_font('Helvetica', 'B', 14)
        for val, label, rc, gc, bc in [
            (n_buy,  'BUY',  16,  163, 74),
            (n_hold, 'HOLD', 100, 116, 139),
            (n_sell, 'SELL', 220, 38,  38),
        ]:
            pdf.set_text_color(rc, gc, bc)
            pdf.cell(col_w, 12, f'{val}  {label}', border=1, align='C')
        pdf.set_text_color(0, 0, 0)
        pdf.ln(10)

        # Actions table
        actions = df[df['decision'].isin(['BUY', 'SELL'])]
        if not actions.empty:
            pdf.set_font('Helvetica', 'B', 13)
            pdf.set_fill_color(241, 245, 249)
            pdf.cell(0, 9, 'Actions Taken Today', fill=True, new_x='LMARGIN', new_y='NEXT')
            pdf.ln(2)

            headers = ['Decision', 'Asset', 'Type', 'Price', 'Confidence']
            widths  = [30, 30, 25, 40, 35]
            pdf.set_font('Helvetica', 'B', 9)
            pdf.set_fill_color(248, 250, 252)
            pdf.set_text_color(100, 116, 139)
            for h, w in zip(headers, widths):
                pdf.cell(w, 7, h, border=1, fill=True, align='C')
            pdf.ln()

            pdf.set_font('Helvetica', '', 9)
            for _, row in actions.iterrows():
                is_buy = row['decision'] == 'BUY'
                r, g, b = (16, 163, 74) if is_buy else (220, 38, 38)
                pdf.set_text_color(r, g, b)
                pdf.cell(widths[0], 7, row['decision'], border=1, align='C')
                pdf.set_text_color(30, 41, 59)
                pdf.cell(widths[1], 7, str(row['asset']),      border=1, align='C')
                pdf.cell(widths[2], 7, str(row['asset_type']), border=1, align='C')
                pdf.cell(widths[3], 7, f"${float(row['price']):,.2f}", border=1, align='C')
                pdf.cell(widths[4], 7, str(int(row['confidence'])), border=1, align='C')
                pdf.ln()
            pdf.ln(6)

    # ── Holdings ───────────────────────────────────────
    if os.path.exists(PORTFOLIO_DETAILS_FILE):
        df = pd.read_csv(PORTFOLIO_DETAILS_FILE)
        if not df.empty:
            df = df.sort_values('return_pct', ascending=False)
            pdf.set_font('Helvetica', 'B', 13)
            pdf.set_fill_color(241, 245, 249)
            pdf.cell(0, 9, 'Current Holdings', fill=True, new_x='LMARGIN', new_y='NEXT')
            pdf.ln(2)

            headers = ['Asset', 'Qty', 'Avg Price', 'Curr Price', 'Value', 'P/L', 'Return %']
            widths  = [22, 18, 28, 28, 28, 28, 28]
            pdf.set_font('Helvetica', 'B', 8)
            pdf.set_fill_color(248, 250, 252)
            pdf.set_text_color(100, 116, 139)
            for h, w in zip(headers, widths):
                pdf.cell(w, 7, h, border=1, fill=True, align='C')
            pdf.ln()

            pdf.set_font('Helvetica', '', 8)
            for _, row in df.iterrows():
                pct  = float(row['return_pct'])
                prof = float(row['profit'])
                sign = '+' if pct >= 0 else ''
                r, g, b = (16, 163, 74) if pct >= 0 else (220, 38, 38)

                pdf.set_text_color(30, 41, 59)
                pdf.cell(widths[0], 7, str(row['asset']),               border=1, align='C')
                pdf.cell(widths[1], 7, str(row['quantity']),            border=1, align='C')
                pdf.cell(widths[2], 7, f"${float(row['average_price']):,.2f}", border=1, align='C')
                pdf.cell(widths[3], 7, f"${float(row['current_price']):,.2f}", border=1, align='C')
                pdf.cell(widths[4], 7, f"${float(row['current_value']):,.2f}", border=1, align='C')
                pdf.set_text_color(r, g, b)
                pdf.cell(widths[5], 7, f"{sign}${prof:,.2f}", border=1, align='C')
                pdf.cell(widths[6], 7, f"{sign}{pct:.2f}%",  border=1, align='C')
                pdf.ln()

    return bytes(pdf.output())

@app.route('/report/download')
@login_required
def download_report():
    pdf_bytes = generate_pdf()
    filename  = f"investment_report_{datetime.now().strftime('%Y-%m-%d')}.pdf"
    response  = make_response(pdf_bytes)
    response.headers['Content-Type']        = 'application/pdf'
    response.headers['Content-Disposition'] = f'attachment; filename={filename}'
    return response

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)

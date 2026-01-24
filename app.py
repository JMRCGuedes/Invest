from flask import Flask, render_template, jsonify
import pandas as pd
import json
import os
from datetime import datetime

app = Flask(__name__)

# File paths
STATE_FILE = "state.json"
PORTFOLIO_SUMMARY_FILE = "portfolio_summary.csv"
PORTFOLIO_DETAILS_FILE = "portfolio_details.csv"
DAILY_SIGNALS_FILE = "daily_signals.csv"
TRADE_HISTORY_FILE = "trade_history.csv"

@app.route('/')
def index():
    """Main dashboard page"""
    return render_template('index.html')

@app.route('/details')
def details():
    """Details page with tables"""
    return render_template('details.html')

@app.route('/api/summary')
def get_summary():
    """Get portfolio summary data"""
    try:
        if os.path.exists(PORTFOLIO_SUMMARY_FILE):
            df = pd.read_csv(PORTFOLIO_SUMMARY_FILE)
            summary = df.to_dict('records')[0]
            return jsonify(summary)
        return jsonify({"error": "Summary file not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/portfolio')
def get_portfolio():
    """Get current portfolio holdings"""
    try:
        if os.path.exists(PORTFOLIO_DETAILS_FILE):
            df = pd.read_csv(PORTFOLIO_DETAILS_FILE)
            portfolio = df.to_dict('records')
            return jsonify(portfolio)
        return jsonify([])
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/signals')
def get_signals():
    """Get latest trading signals"""
    try:
        if os.path.exists(DAILY_SIGNALS_FILE):
            df = pd.read_csv(DAILY_SIGNALS_FILE)
            signals = df.to_dict('records')
            return jsonify(signals)
        return jsonify([])
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/trade-history')
def get_trade_history():
    """Get trade history (last 100 trades)"""
    try:
        if os.path.exists(TRADE_HISTORY_FILE):
            df = pd.read_csv(TRADE_HISTORY_FILE)
            # Get last 100 trades
            trades = df.tail(100).to_dict('records')
            return jsonify(trades)
        return jsonify([])
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/assets')
def get_assets():
    """Get list of all assets that have trading history"""
    try:
        if not os.path.exists(TRADE_HISTORY_FILE):
            return jsonify([])
        
        df = pd.read_csv(TRADE_HISTORY_FILE)
        # Get unique assets sorted alphabetically
        assets = sorted(df['asset'].unique().tolist())
        return jsonify(assets)
    except Exception as e:
        print(f"Error getting assets: {e}")
        return jsonify([])

@app.route('/api/asset-performance/<asset>')
def get_asset_performance(asset):
    """Get profit/loss performance over time for a specific asset"""
    try:
        if not os.path.exists(TRADE_HISTORY_FILE):
            return jsonify([])
        
        df = pd.read_csv(TRADE_HISTORY_FILE)
        df = df[df['asset'] == asset].copy()
        
        if df.empty:
            return jsonify([])
        
        # Sort by date
        df['date_dt'] = pd.to_datetime(df['date'])
        df = df.sort_values('date_dt')
        
        # Calculate cumulative performance
        position = 0  # Current position (shares held)
        total_cost = 0  # Total money spent on current position
        cumulative_profit = 0  # Total profit/loss over all trades
        
        results = []
        
        for _, row in df.iterrows():
            decision = row['decision']
            price = float(row['price'])
            date = row['date_dt'].strftime('%Y-%m-%d')
            
            if decision == 'BUY' and position == 0:
                # Start a new position
                position = 1
                total_cost = price
                results.append({
                    'date': date,
                    'decision': 'BUY',
                    'price': price,
                    'cumulative_profit': round(cumulative_profit, 2),
                    'position_value': round(price, 2)
                })
            elif decision == 'SELL' and position > 0:
                # Close position and calculate profit
                profit = price - total_cost
                cumulative_profit += profit
                position = 0
                total_cost = 0
                results.append({
                    'date': date,
                    'decision': 'SELL',
                    'price': price,
                    'cumulative_profit': round(cumulative_profit, 2),
                    'position_value': 0
                })
            elif position > 0:
                # Update position value
                results.append({
                    'date': date,
                    'decision': decision,
                    'price': price,
                    'cumulative_profit': round(cumulative_profit, 2),
                    'position_value': round(price, 2)
                })
        
        # Limit to last 50 entries for performance
        return jsonify(results[-50:] if len(results) > 50 else results)
        
    except Exception as e:
        print(f"Error in asset-performance: {e}")
        return jsonify([])

@app.route('/api/asset-history/<asset>')
def get_asset_history(asset):
    """Get last 30 days of trading history for a specific asset"""
    try:
        if not os.path.exists(TRADE_HISTORY_FILE):
            return jsonify([])
        
        df = pd.read_csv(TRADE_HISTORY_FILE)
        
        # Filter for specific asset
        df = df[df['asset'] == asset]
        
        if df.empty:
            return jsonify([])
        
        # Convert date and sort
        df['date_only'] = pd.to_datetime(df['date']).dt.date
        df = df.sort_values('date_only')
        
        # Group by date and get the most recent decision/price for each day
        daily_data = {}
        for _, row in df.iterrows():
            date = row['date_only']
            daily_data[date] = {
                'date': str(date),
                'decision': row['decision'],
                'confidence': int(row['confidence']),
                'price': float(row['price'])
            }
        
        # Convert to list and get last 30 days only
        result = list(daily_data.values())
        result = result[-30:] if len(result) > 30 else result
        
        return jsonify(result)
    except Exception as e:
        print(f"Error in asset-history: {e}")
        return jsonify([])

@app.route('/api/asset-allocation')
def get_asset_allocation():
    """Get asset allocation data for pie chart"""
    try:
        if os.path.exists(PORTFOLIO_DETAILS_FILE):
            df = pd.read_csv(PORTFOLIO_DETAILS_FILE)
            allocation = df[['asset', 'current_value']].to_dict('records')
            return jsonify(allocation)
        return jsonify([])
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)

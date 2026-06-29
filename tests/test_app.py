"""Unit tests for the dashboard Flask app (app.py)."""
import json
import pytest
import pandas as pd
from unittest.mock import patch, MagicMock
from app import app, generate_pdf, INITIAL_CAPITAL

# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def client():
    app.config['TESTING'] = True
    app.config['SECRET_KEY'] = 'test-secret'
    with app.test_client() as c:
        yield c

@pytest.fixture
def auth_client(client):
    """Client with an active session."""
    with client.session_transaction() as sess:
        sess['username'] = 'João Guedes'
    return client

# ── Sample DataFrames ──────────────────────────────────────────────────────────

def _summary_df():
    return pd.DataFrame([{
        'available_cash': 5000.0,
        'portfolio_value': 6000.0,
        'total_invested': 4000.0,
        'total_profit': 1000.0,
    }])

def _portfolio_df():
    return pd.DataFrame([{
        'asset': 'AAPL',
        'quantity': 10,
        'average_price': 150.0,
        'current_price': 160.0,
        'current_value': 1600.0,
        'profit': 100.0,
        'return_pct': 6.67,
    }])

def _signals_df():
    return pd.DataFrame([
        {'asset': 'AAPL', 'decision': 'BUY',  'price': 150.0, 'confidence': 80, 'date': '2026-06-29', 'asset_type': 'stock'},
        {'asset': 'MSFT', 'decision': 'HOLD', 'price': 300.0, 'confidence': 60, 'date': '2026-06-29', 'asset_type': 'stock'},
        {'asset': 'TSLA', 'decision': 'SELL', 'price': 200.0, 'confidence': 75, 'date': '2026-06-29', 'asset_type': 'stock'},
    ])

def _trade_history_df():
    return pd.DataFrame([
        {'asset': 'AAPL', 'decision': 'BUY',  'price': 140.0, 'confidence': 80, 'date': '2026-01-01'},
        {'asset': 'AAPL', 'decision': 'HOLD', 'price': 145.0, 'confidence': 65, 'date': '2026-01-02'},
        {'asset': 'AAPL', 'decision': 'SELL', 'price': 160.0, 'confidence': 70, 'date': '2026-01-10'},
        {'asset': 'MSFT', 'decision': 'BUY',  'price': 290.0, 'confidence': 85, 'date': '2026-02-01'},
    ])

# ── Auth ───────────────────────────────────────────────────────────────────────

class TestLogin:
    def test_get_login_page_renders(self, client):
        resp = client.get('/login')
        assert resp.status_code == 200

    def test_valid_credentials_redirect_to_index(self, client):
        resp = client.post('/login', data={'username': 'João Guedes', 'password': 'admin'})
        assert resp.status_code == 302
        assert '/' in resp.headers['Location']

    def test_invalid_password_stays_on_login(self, client):
        resp = client.post('/login', data={'username': 'João Guedes', 'password': 'wrong'})
        assert resp.status_code == 200
        assert b'Invalid' in resp.data

    def test_unknown_user_stays_on_login(self, client):
        resp = client.post('/login', data={'username': 'nobody', 'password': 'admin'})
        assert resp.status_code == 200
        assert b'Invalid' in resp.data

    def test_already_logged_in_redirects_to_index(self, auth_client):
        resp = auth_client.get('/login')
        assert resp.status_code == 302
        assert '/' in resp.headers['Location']


class TestLogout:
    def test_logout_clears_session_and_redirects(self, auth_client):
        resp = auth_client.get('/logout')
        assert resp.status_code == 302
        with auth_client.session_transaction() as sess:
            assert 'username' not in sess


# ── Page routes ────────────────────────────────────────────────────────────────

class TestPageRoutes:
    @pytest.mark.parametrize('url', ['/', '/details', '/notifications'])
    def test_unauthenticated_redirects_to_login(self, client, url):
        resp = client.get(url)
        assert resp.status_code == 302
        assert 'login' in resp.headers['Location']

    def test_index_renders_for_authenticated_user(self, auth_client):
        resp = auth_client.get('/')
        assert resp.status_code == 200
        assert b'Investment Portfolio' in resp.data

    def test_details_renders_for_authenticated_user(self, auth_client):
        resp = auth_client.get('/details')
        assert resp.status_code == 200

    def test_notifications_renders_for_authenticated_user(self, auth_client):
        resp = auth_client.get('/notifications')
        assert resp.status_code == 200


# ── /api/summary ───────────────────────────────────────────────────────────────

class TestSummaryEndpoint:
    def test_unauthenticated_redirects(self, client):
        resp = client.get('/api/summary')
        assert resp.status_code == 302

    def test_returns_summary_data(self, auth_client):
        with patch('app.os.path.exists', return_value=True), \
             patch('app.pd.read_csv', return_value=_summary_df()):
            resp = auth_client.get('/api/summary')
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data['available_cash'] == 5000.0
        assert data['total_profit'] == 1000.0

    def test_missing_file_returns_404(self, auth_client):
        with patch('app.os.path.exists', return_value=False):
            resp = auth_client.get('/api/summary')
        assert resp.status_code == 404
        assert b'error' in resp.data


# ── /api/portfolio ─────────────────────────────────────────────────────────────

class TestPortfolioEndpoint:
    def test_returns_portfolio_list(self, auth_client):
        with patch('app.os.path.exists', return_value=True), \
             patch('app.pd.read_csv', return_value=_portfolio_df()):
            resp = auth_client.get('/api/portfolio')
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert len(data) == 1
        assert data[0]['asset'] == 'AAPL'

    def test_missing_file_returns_empty_list(self, auth_client):
        with patch('app.os.path.exists', return_value=False):
            resp = auth_client.get('/api/portfolio')
        assert resp.status_code == 200
        assert json.loads(resp.data) == []


# ── /api/signals ───────────────────────────────────────────────────────────────

class TestSignalsEndpoint:
    def test_returns_signal_list(self, auth_client):
        with patch('app.os.path.exists', return_value=True), \
             patch('app.pd.read_csv', return_value=_signals_df()):
            resp = auth_client.get('/api/signals')
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert len(data) == 3
        decisions = {r['decision'] for r in data}
        assert decisions == {'BUY', 'HOLD', 'SELL'}

    def test_missing_file_returns_empty_list(self, auth_client):
        with patch('app.os.path.exists', return_value=False):
            resp = auth_client.get('/api/signals')
        assert resp.status_code == 200
        assert json.loads(resp.data) == []


# ── /api/trade-history ─────────────────────────────────────────────────────────

class TestTradeHistoryEndpoint:
    def test_returns_last_100_records(self, auth_client):
        df = pd.concat([_trade_history_df()] * 30, ignore_index=True)  # 120 rows
        with patch('app.os.path.exists', return_value=True), \
             patch('app.pd.read_csv', return_value=df):
            resp = auth_client.get('/api/trade-history')
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert len(data) == 100

    def test_missing_file_returns_empty_list(self, auth_client):
        with patch('app.os.path.exists', return_value=False):
            resp = auth_client.get('/api/trade-history')
        assert resp.status_code == 200
        assert json.loads(resp.data) == []


# ── /api/assets ────────────────────────────────────────────────────────────────

class TestAssetsEndpoint:
    def test_returns_sorted_unique_assets(self, auth_client):
        with patch('app.os.path.exists', return_value=True), \
             patch('app.pd.read_csv', return_value=_trade_history_df()):
            resp = auth_client.get('/api/assets')
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data == sorted(data)
        assert 'AAPL' in data
        assert 'MSFT' in data

    def test_missing_file_returns_empty_list(self, auth_client):
        with patch('app.os.path.exists', return_value=False):
            resp = auth_client.get('/api/assets')
        assert resp.status_code == 200
        assert json.loads(resp.data) == []


# ── /api/asset-performance/<asset> ────────────────────────────────────────────

class TestAssetPerformanceEndpoint:
    def test_computes_cumulative_profit_after_sell(self, auth_client):
        with patch('app.os.path.exists', return_value=True), \
             patch('app.pd.read_csv', return_value=_trade_history_df()):
            resp = auth_client.get('/api/asset-performance/AAPL')
        assert resp.status_code == 200
        data = json.loads(resp.data)
        sell_row = next(r for r in data if r['decision'] == 'SELL')
        assert sell_row['cumulative_profit'] == round(160.0 - 140.0, 2)

    def test_missing_file_returns_empty_list(self, auth_client):
        with patch('app.os.path.exists', return_value=False):
            resp = auth_client.get('/api/asset-performance/AAPL')
        assert resp.status_code == 200
        assert json.loads(resp.data) == []

    def test_unknown_asset_returns_empty_list(self, auth_client):
        with patch('app.os.path.exists', return_value=True), \
             patch('app.pd.read_csv', return_value=_trade_history_df()):
            resp = auth_client.get('/api/asset-performance/UNKNOWN')
        assert resp.status_code == 200
        assert json.loads(resp.data) == []

    def test_capped_at_50_results(self, auth_client):
        dates = pd.date_range('2026-01-01', periods=60).strftime('%Y-%m-%d').tolist()
        rows = [{'asset': 'X', 'decision': 'HOLD', 'price': 100.0,
                 'confidence': 50, 'date': d} for d in dates]
        rows[0]['decision'] = 'BUY'
        df = pd.DataFrame(rows)
        with patch('app.os.path.exists', return_value=True), \
             patch('app.pd.read_csv', return_value=df):
            resp = auth_client.get('/api/asset-performance/X')
        assert len(json.loads(resp.data)) == 50


# ── /api/asset-history/<asset> ────────────────────────────────────────────────

class TestAssetHistoryEndpoint:
    def test_returns_deduplicated_daily_records(self, auth_client):
        with patch('app.os.path.exists', return_value=True), \
             patch('app.pd.read_csv', return_value=_trade_history_df()):
            resp = auth_client.get('/api/asset-history/AAPL')
        assert resp.status_code == 200
        data = json.loads(resp.data)
        # AAPL has 3 distinct dates in the fixture (2026-01-01, 2026-01-02, 2026-01-10)
        assert len(data) == 3

    def test_capped_at_30_results(self, auth_client):
        dates = pd.date_range('2026-01-01', periods=40).strftime('%Y-%m-%d').tolist()
        rows = [{'asset': 'X', 'decision': 'HOLD', 'price': 100.0,
                 'confidence': 50, 'date': d} for d in dates]
        df = pd.DataFrame(rows)
        with patch('app.os.path.exists', return_value=True), \
             patch('app.pd.read_csv', return_value=df):
            resp = auth_client.get('/api/asset-history/X')
        assert len(json.loads(resp.data)) == 30

    def test_missing_file_returns_empty_list(self, auth_client):
        with patch('app.os.path.exists', return_value=False):
            resp = auth_client.get('/api/asset-history/AAPL')
        assert json.loads(resp.data) == []


# ── /api/asset-allocation ─────────────────────────────────────────────────────

class TestAssetAllocationEndpoint:
    def test_returns_asset_and_value_columns(self, auth_client):
        with patch('app.os.path.exists', return_value=True), \
             patch('app.pd.read_csv', return_value=_portfolio_df()):
            resp = auth_client.get('/api/asset-allocation')
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data[0]['asset'] == 'AAPL'
        assert data[0]['current_value'] == 1600.0
        assert 'quantity' not in data[0]

    def test_missing_file_returns_empty_list(self, auth_client):
        with patch('app.os.path.exists', return_value=False):
            resp = auth_client.get('/api/asset-allocation')
        assert json.loads(resp.data) == []


# ── /api/asset-stats ──────────────────────────────────────────────────────────

class TestAssetStatsEndpoint:
    def test_returns_hold_time_and_profitability(self, auth_client):
        with patch('app.os.path.exists', return_value=True), \
             patch('app.pd.read_csv', return_value=_trade_history_df()):
            resp = auth_client.get('/api/asset-stats')
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert 'hold_time' in data
        assert 'profitability' in data

    def test_closed_trade_appears_in_profitability(self, auth_client):
        with patch('app.os.path.exists', return_value=True), \
             patch('app.pd.read_csv', return_value=_trade_history_df()):
            resp = auth_client.get('/api/asset-stats')
        data = json.loads(resp.data)
        assets_with_profit = [r['asset'] for r in data['profitability']]
        assert 'AAPL' in assets_with_profit

    def test_open_position_excluded_from_profitability(self, auth_client):
        with patch('app.os.path.exists', return_value=True), \
             patch('app.pd.read_csv', return_value=_trade_history_df()):
            resp = auth_client.get('/api/asset-stats')
        data = json.loads(resp.data)
        assets_with_profit = [r['asset'] for r in data['profitability']]
        # MSFT only has a BUY, no SELL — should not appear
        assert 'MSFT' not in assets_with_profit

    def test_missing_file_returns_empty_structure(self, auth_client):
        with patch('app.os.path.exists', return_value=False):
            resp = auth_client.get('/api/asset-stats')
        data = json.loads(resp.data)
        assert data == {'hold_time': [], 'profitability': []}


# ── /api/notifications ────────────────────────────────────────────────────────

class TestNotificationsEndpoint:
    def test_returns_only_buy_and_sell_actions(self, auth_client):
        with patch('app.os.path.exists', return_value=True), \
             patch('app.pd.read_csv', return_value=_signals_df()):
            resp = auth_client.get('/api/notifications')
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert len(data) == 2
        for item in data:
            assert item['type'] in ('BUY', 'SELL')

    def test_notification_fields_present(self, auth_client):
        with patch('app.os.path.exists', return_value=True), \
             patch('app.pd.read_csv', return_value=_signals_df()):
            resp = auth_client.get('/api/notifications')
        data = json.loads(resp.data)
        for item in data:
            assert {'type', 'asset', 'price', 'confidence', 'date'} <= item.keys()

    def test_missing_file_returns_empty_list(self, auth_client):
        with patch('app.os.path.exists', return_value=False):
            resp = auth_client.get('/api/notifications')
        assert json.loads(resp.data) == []


# ── /report/download ──────────────────────────────────────────────────────────

class TestReportDownload:
    def test_unauthenticated_redirects(self, client):
        resp = client.get('/report/download')
        assert resp.status_code == 302

    def test_authenticated_returns_pdf_bytes(self, auth_client):
        with patch('app.os.path.exists', return_value=False):
            resp = auth_client.get('/report/download')
        assert resp.status_code == 200
        assert resp.content_type == 'application/pdf'
        assert resp.data[:4] == b'%PDF'

    def test_pdf_with_all_data(self, auth_client):
        def _mock_exists(path):
            return True

        def _mock_read_csv(path):
            if 'summary' in path:
                return _summary_df()
            if 'details' in path:
                return _portfolio_df()
            if 'signals' in path:
                return _signals_df()
            return _trade_history_df()

        with patch('app.os.path.exists', side_effect=_mock_exists), \
             patch('app.pd.read_csv', side_effect=_mock_read_csv):
            resp = auth_client.get('/report/download')

        assert resp.status_code == 200
        assert resp.data[:4] == b'%PDF'
        assert 'attachment' in resp.headers['Content-Disposition']


# ── generate_pdf (unit) ───────────────────────────────────────────────────────

class TestGeneratePdf:
    def test_returns_bytes(self):
        with patch('app.os.path.exists', return_value=False):
            result = generate_pdf()
        assert isinstance(result, bytes)
        assert result[:4] == b'%PDF'

    def _pdf_read_csv(self, summary_df):
        """Return different DataFrames per file to satisfy generate_pdf's multiple reads."""
        def _side_effect(path):
            if 'summary' in path:
                return summary_df
            if 'signals' in path:
                return _signals_df()
            if 'details' in path:
                return _portfolio_df()
            return pd.DataFrame()
        return _side_effect

    def test_profit_positive_renders(self):
        with patch('app.os.path.exists', return_value=True), \
             patch('app.pd.read_csv', side_effect=self._pdf_read_csv(_summary_df())):
            result = generate_pdf()
        assert isinstance(result, bytes)

    def test_profit_negative_renders(self):
        df = _summary_df().copy()
        df['total_profit'] = -500.0
        with patch('app.os.path.exists', return_value=True), \
             patch('app.pd.read_csv', side_effect=self._pdf_read_csv(df)):
            result = generate_pdf()
        assert isinstance(result, bytes)

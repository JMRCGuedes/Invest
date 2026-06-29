# Code Review — `app.py` (Flask Paper-Trading Dashboard)

Reviewed file: `app.py` (Flask UI). Supporting context: CSV data files
(`portfolio_summary.csv`, `portfolio_details.csv`, `daily_signals.csv`,
`trade_history.csv`), `state.json`, and a concurrent writer `investment_bot.py`
that regenerates the CSVs (hourly GitHub Actions run).

Findings are grouped by category and prioritised **High / Medium / Low**.
This document only *describes* recommended changes — none are implemented.

---

## 1. Security

### [HIGH] Hardcoded fallback secret key in source
A predictable fallback secret key lets anyone forge session cookies if
`SECRET_KEY` is not set in the environment.

```python
# Current
app.secret_key = os.environ.get('SECRET_KEY', 'invest-portfolio-secret-key-2026')
```
```python
# Recommended — fail closed, no guessable default
app.secret_key = os.environ['SECRET_KEY']  # raise at startup if missing
# or generate a random key and refuse to start in production without one
```

### [HIGH] Plaintext credentials stored and compared in source
The single user's password lives in the source as cleartext and is compared
with `==` (also not constant-time). Anyone with repo read access has the login.

```python
# Current
USERS = {"João Guedes": "admin"}
...
if username in USERS and USERS[username] == password:
```
```python
# Recommended — store a hash, compare with a constant-time verifier
from werkzeug.security import check_password_hash
USERS = {"João Guedes": os.environ["ADMIN_PW_HASH"]}  # pbkdf2/scrypt hash
if username in USERS and check_password_hash(USERS[username], password):
```

### [HIGH] `debug=True` and `host='0.0.0.0'` in the run block
Debug mode exposes the Werkzeug interactive debugger (arbitrary code execution
via the console PIN) and auto-reloader; binding to `0.0.0.0` exposes it on all
interfaces. This must never run in production.

```python
# Current
app.run(debug=True, host='0.0.0.0', port=5000)
```
```python
# Recommended — debug from env, serve via gunicorn (already a dependency)
app.run(debug=os.environ.get("FLASK_DEBUG") == "1", host="127.0.0.1", port=5000)
# Production: gunicorn 'app:app'  (no app.run)
```

### [MEDIUM] Exception text leaked to clients
Several endpoints return `str(e)` in the JSON body, disclosing internal paths,
stack details, and pandas internals to the caller.

```python
# Current
except Exception as e:
    return jsonify({"error": str(e)}), 500
```
```python
# Recommended — log the detail, return a generic message
except Exception:
    app.logger.exception("summary endpoint failed")
    return jsonify({"error": "internal error"}), 500
```

### [MEDIUM] No brute-force protection / rate limiting on login
The `/login` POST has no throttling or lockout, so the single account can be
brute-forced. Add `flask-limiter` (e.g. 5 attempts/min/IP) and consider a
short delay on failure.

### [MEDIUM] Session cookie hardening not configured
No `SESSION_COOKIE_SECURE`, `HTTPONLY`, `SAMESITE`, or session lifetime is set.

```python
# Recommended
app.config.update(
    SESSION_COOKIE_SECURE=True,      # HTTPS only
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    PERMANENT_SESSION_LIFETIME=timedelta(hours=8),
)
```

### [MEDIUM] No CSRF protection on the login form
The POST form has no CSRF token. Add `flask-wtf`'s `CSRFProtect` (also covers
any future state-changing endpoints).

### [LOW] `/report/download` sets headers manually
Using `make_response` + manual headers is fine, but `send_file` /
`Response(..., mimetype=...)` is less error-prone and `filename` should be
quoted in `Content-Disposition` to be safe.

---

## 2. Code Quality / Maintainability

### [HIGH] Unfinished `generate_pdf()` — literal `...` placeholders
The "Signal Summary" and "Holdings" sections contain bare `...` ellipsis
literals. These are no-ops: the PDF silently omits those sections, and the
computed `n_buy/n_sell/n_hold` and the holdings DataFrame are read but never
used (dead work).

```python
# Current
n_hold = int((df['decision'] == 'HOLD').sum())
...
# ── Holdings ──
df = pd.read_csv(PORTFOLIO_DETAILS_FILE)
...
```
```python
# Recommended — implement the table rendering, or remove the dead blocks
pdf.cell(0, 8, f"Signals  BUY: {n_buy}   SELL: {n_sell}   HOLD: {n_hold}",
         new_x='LMARGIN', new_y='NEXT')
# ...render holdings rows...
```

### [HIGH] Massive duplication across API endpoints
Nearly every endpoint repeats the same "exists? read_csv -> to_dict / else
empty" boilerplate with subtly inconsistent behaviour. Extract a helper.

```python
# Current (repeated ~8 times)
try:
    if os.path.exists(PORTFOLIO_DETAILS_FILE):
        df = pd.read_csv(PORTFOLIO_DETAILS_FILE)
        return jsonify(df.to_dict('records'))
    return jsonify([])
except Exception as e:
    return jsonify({"error": str(e)}), 500
```
```python
# Recommended
def load_csv(path) -> pd.DataFrame:
    return pd.read_csv(path) if os.path.exists(path) else pd.DataFrame()

@app.route('/api/portfolio')
@login_required
def get_portfolio():
    return jsonify(load_csv(PORTFOLIO_DETAILS_FILE).to_dict('records'))
```

### [MEDIUM] Inconsistent error contract
Missing-file and error cases differ per endpoint: some return `[]`, some
`{"error": ...}, 404`, some `{"error": ...}, 500`, and `get_assets` has a
*second* bare `except` returning `[]`. Pick one contract (e.g. always a list /
always an object with an `error` key) so the frontend can handle it uniformly.

### [MEDIUM] Dead code: `_col()` helper is never called
`_col(value, pos, neg)` is defined but unused; the PDF inlines its own color
logic. Remove it or use it.

### [LOW] No logging configured
There is no `logging` setup; failures are swallowed into JSON responses with no
server-side trail. Configure `app.logger` and log all caught exceptions.

### [LOW] Magic numbers / repeated literals in PDF code
RGB tuples, column widths, and the same currency-format expressions are
repeated. Factor colors and a `money(x)` formatter into named constants/helpers.

### [LOW] Missing docstrings / type hints
Only one endpoint has a docstring. Adding type hints and brief docstrings would
aid maintenance, especially around the non-trivial `asset-performance` and
`asset-stats` logic.

---

## 3. Performance

### [HIGH] CSV files re-read from disk on every request, uncached
`trade_history.csv` is ~258 KB and is fully parsed by pandas on *every* call to
`/api/assets`, `/api/asset-performance`, `/api/asset-history`, and
`/api/asset-stats`. Under any concurrency this is wasteful and slow.

```python
# Recommended — cache with mtime-based invalidation (data changes hourly)
from functools import lru_cache
def read_csv_cached(path):
    return _load(path, os.path.getmtime(path))  # mtime busts the cache

@lru_cache(maxsize=8)
def _load(path, _mtime):
    return pd.read_csv(path)
```
Alternatively add HTTP caching headers, or use `flask-caching` with a short TTL.

### [MEDIUM] `df.iterrows()` used for aggregation
`asset-performance`, `asset-history`, and `asset-stats` loop with `iterrows()`,
which is the slowest pandas access pattern. The position/profit walk is
inherently sequential, but per-asset grouping in `asset-stats` can use
`groupby` and vectorised operations to cut overhead substantially.

### [LOW] Whole-frame `to_dict('records')`
Endpoints serialise entire frames. Only the columns the UI needs should be
selected before `to_dict` (e.g. `asset-allocation` already does this — apply
the same elsewhere).

---

## 4. Correctness / Edge Cases

### [HIGH] `position`/profit logic ignores quantity (assumes 1 unit)
`get_asset_performance` and `asset-stats` treat every position as a single
unit (`position = 1`, `total_cost = price`, profit = `price - total_cost`).
There is no `quantity` column in `trade_history.csv`, so P/L and cumulative
profit are per-share deltas, not actual position P/L. This will misreport
returns whenever real position sizing differs. Confirm the intended unit and
incorporate quantity (or document that values are per-unit).

```python
# Current
if decision == 'BUY' and position == 0:
    position = 1
    total_cost = price
elif decision == 'SELL' and position > 0:
    cumulative_profit += price - total_cost   # per-share only
```

### [HIGH] `total_profit` percentage uses a hardcoded base
The PDF computes `profit_pct = profit / INITIAL_CAPITAL * 100` against the
fixed `10_000` constant rather than current invested/portfolio value. If
capital was added/withdrawn or the base differs, the percentage is wrong.
Derive the denominator from the data (`total_invested` or starting equity).

### [MEDIUM] `records[0]` raises on an empty summary file
`get_summary` does `df.to_dict('records')[0]`; an existing-but-empty CSV throws
`IndexError`, caught only by the generic 500 handler.

```python
# Recommended
recs = df.to_dict('records')
if not recs:
    return jsonify({"error": "no summary data"}), 404
return jsonify(recs[0])
```

### [MEDIUM] NaN values produce invalid JSON
`jsonify` serialises pandas `NaN` as the bare token `NaN`, which is not valid
JSON and breaks strict parsers. Replace before serialising:

```python
df = df.where(pd.notnull(df), None)   # NaN -> null
```

### [MEDIUM] `int(row['confidence'])` / `float(row['price'])` assume clean data
A missing/`NaN` `confidence` or `price` raises `ValueError`, failing the whole
request (silently for endpoints that swallow to `[]`). Coerce defensively with
`pd.to_numeric(..., errors='coerce')` and skip/again default bad rows.

### [LOW] `pd.to_datetime` without an explicit format
Relying on inference can misparse ambiguous dates and emits future-version
warnings. Pass `format=...` matching the bot's output for safety and speed.

### [LOW] Dangling open positions excluded from stats
`asset-stats` only counts closed BUY/SELL pairs; an asset bought and still held
contributes 0 hold-days and no profit. That may be intended, but worth a UI
note so "missing" assets aren't read as a bug.

---

## 5. Architecture

### [MEDIUM] CSV-as-database with a concurrent writer (race conditions)
`investment_bot.py` rewrites these CSVs on a schedule while the Flask app reads
them. A read during a partial write can yield a truncated/garbled file and a
parse error. Mitigate with atomic writes in the bot (write temp file +
`os.replace`) and/or a read-retry, or move to SQLite (atomic, concurrent-read
friendly) which also enables the caching/indexing wins above.

### [MEDIUM] Single-file app, no separation of concerns
Routing, auth, data access, and PDF generation all live in one module. As this
grows, split into Blueprints (`auth`, `api`, `reports`) and a small data-access
layer wrapping the CSV/DB reads. This also makes the existing `tests/` dir
easier to target.

### [LOW] Auth state is an in-memory dict, single user
`USERS` is hardcoded for one operator. Acceptable for a personal tool, but if
multi-user or rotation is ever needed, move to a config/secret store or DB.

### [LOW] Configuration scattered / partially hardcoded
Only `SECRET_KEY` comes from the environment; file paths, `INITIAL_CAPITAL`,
debug, and host are hardcoded. Centralise into a `Config` class driven by env
vars for portability across local/CI/production.

---

## Summary of Priorities

| Priority | Items |
|----------|-------|
| **High** | Hardcoded secret-key fallback; plaintext password + `==` compare; `debug=True`/`0.0.0.0`; unfinished `generate_pdf` (`...` placeholders); endpoint duplication; uncached CSV reads; quantity-agnostic P/L; hardcoded profit-% base |
| **Medium** | Leaked exception text; no login rate limiting; no session-cookie hardening; no CSRF; inconsistent error contract; `records[0]` IndexError; NaN -> invalid JSON; unsafe numeric coercion; CSV write/read races; single-file structure |
| **Low** | Dead `_col` helper; no logging; magic numbers; missing docstrings/type hints; full-frame serialisation; `to_datetime` format; excluded open positions; in-memory single user; scattered config |

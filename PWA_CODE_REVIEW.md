# Code Review — PWA Feature

Reviewed commits:
- `7693749` *Make app into a PWA*: `static/manifest.json`, `static/sw.js`,
  `static/icon.svg`, the `/sw.js` route in `app.py`, and the `<head>` tags in
  all four templates.
- `238e0ea` *Fix the layout to be responsive*: the safe-area and bottom-nav CSS
  in `static/style.css`, and the `<nav class="bottom-nav">` markup.

Findings are prioritised **High / Medium / Low**. This document only
*describes* recommended changes; none of them are implemented yet. Section 6
lists future improvements that go beyond fixing what's there.

---

## 1. Installability & Icons

### [HIGH] `apple-touch-icon` points to an SVG, which iOS does not support
iOS Safari ignores SVG `apple-touch-icon`s. When you "Add to Home Screen",
it falls back to a screenshot of the page (or a generic letter tile), so the
installed app has no proper icon on iPhone/iPad.

```html
<!-- Current (all 4 templates) -->
<link rel="apple-touch-icon" href="{{ url_for('static', filename='icon.svg') }}">
```
```html
<!-- Recommended: 180×180 PNG rendered from icon.svg -->
<link rel="apple-touch-icon" sizes="180x180" href="{{ url_for('static', filename='icons/apple-touch-icon.png') }}">
```

### [MEDIUM] Manifest only has one SVG icon: no PNG sizes, no maskable icon
Current Chrome accepts an SVG with `"sizes": "any"`, but:
- Older Android/Chromium builds, Samsung Internet and some WebAPK paths
  expect raster **192×192** and **512×512** PNGs.
- There is no `"purpose": "maskable"` icon. Android therefore shrinks the
  icon inside a white circle or squircle instead of filling the adaptive-icon
  shape. The current SVG has `rx="80"` rounded corners and content close to
  the edges, so it also isn't safe to reuse as maskable.

```json
"icons": [
  { "src": "/static/icons/icon-192.png", "sizes": "192x192", "type": "image/png", "purpose": "any" },
  { "src": "/static/icons/icon-512.png", "sizes": "512x512", "type": "image/png", "purpose": "any" },
  { "src": "/static/icons/icon-maskable-512.png", "sizes": "512x512", "type": "image/png", "purpose": "maskable" },
  { "src": "/static/icon.svg", "sizes": "any", "type": "image/svg+xml", "purpose": "any" }
]
```
For the maskable variant, use a full-bleed square background with the
chart line inside the central ~80% safe zone. You can check it with
maskable.app.

### [MEDIUM] Manifest is missing `id` and `scope`
Without `id`, the browser derives the app's identity from `start_url`. If
`start_url` ever changes (for example to `/?source=pwa`), users end up with
a second, separate installed app. An explicit `scope` also makes clear which
URLs stay inside the standalone window.

```json
"id": "/",
"start_url": "/",
"scope": "/",
```

### [LOW] `orientation: "portrait"` locks the app
The Details page has wide tables and charts that are easier to read in
landscape, and the lock applies to tablets too. Remove it (the default is
`any`) unless portrait-only is a deliberate choice.

---

## 2. Service Worker (`static/sw.js`)

### [MEDIUM] The pass-through `fetch` handler adds cost and no benefit
```js
self.addEventListener('fetch', e => e.respondWith(fetch(e.request)));
```
- Chrome stopped requiring a `fetch` handler for installability in 2023, so
  the handler isn't needed for install.
- A no-op handler makes **every** request (pages, API calls, CSS/JS) start
  the SW and go through it, which adds latency, especially on cold start.
  Chrome DevTools flags this as a "no-op fetch handler".
- When offline, `fetch()` rejects and `respondWith` gets a rejected promise.
  The installed app then shows the browser's generic network-error page
  with no explanation.

**Option A (minimal):** delete the `fetch` listener.
**Option B (recommended):** keep it only for navigations and serve an
offline fallback page:

```js
const OFFLINE_CACHE = 'offline-v1';
const OFFLINE_URL = '/static/offline.html';

self.addEventListener('install', e => {
  e.waitUntil(caches.open(OFFLINE_CACHE).then(c => c.add(OFFLINE_URL)));
  self.skipWaiting();
});

self.addEventListener('activate', e => {
  e.waitUntil((async () => {
    const keys = await caches.keys();
    await Promise.all(keys.filter(k => k !== OFFLINE_CACHE).map(k => caches.delete(k)));
    await self.clients.claim();
  })());
});

self.addEventListener('fetch', e => {
  if (e.request.mode !== 'navigate') return;   // let the browser handle everything else
  e.respondWith(fetch(e.request).catch(() => caches.match(OFFLINE_URL)));
});
```
`offline.html` must be a static file with no auth and no user data, so
caching it is safe. That fits the comment's intent of "no caching of
auth-protected pages".

### [LOW] `Service-Worker-Allowed: /` header is redundant
The worker is already served from `/sw.js`, so its default scope is `/`.
The header is only needed when a script at a deeper path (such as
`/static/sw.js`) wants a wider scope. It's harmless, but it can go. If you
keep the header, register with an explicit `{ scope: '/' }` so the intent is
clear.

### [LOW] Registration errors are unhandled
```html
<script>if ('serviceWorker' in navigator) navigator.serviceWorker.register('/sw.js');</script>
```
A failed registration (bad deploy, HTTP instead of HTTPS, private mode)
causes an unhandled promise rejection. Add
`.catch(err => console.warn('SW registration failed', err))`.

### [LOW] No versioning / update strategy
`skipWaiting()` + `clients.claim()` activates a new worker immediately.
That's fine for a pass-through worker. Once the worker starts caching
(Option B above, or §6), add a `CACHE_VERSION` constant and delete old caches
in `activate`, as shown in Option B. Otherwise stale assets can outlive a
deploy.

---

## 3. iOS Standalone Layout

### [MEDIUM] `env(safe-area-inset-*)` is always 0: `viewport-fit=cover` is missing
`238e0ea` pads the navbar and bottom-nav with `env(safe-area-inset-top)` and
`env(safe-area-inset-bottom)`. iOS only reports non-zero insets when the
viewport opts in with `viewport-fit=cover`. All four templates currently use:

```html
<meta name="viewport" content="width=device-width, initial-scale=1.0">
```

At the same time, `apple-mobile-web-app-status-bar-style="black-translucent"`
makes the page draw *under* the status bar. On notched iPhones in standalone
mode, the top of the navbar can therefore sit behind the clock or Dynamic
Island, and the bottom nav can overlap the home indicator.

```html
<!-- Recommended -->
<meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover">
```
Test this on a real device (or the Xcode simulator) in standalone mode after
the change.

### [LOW] Add the standard `mobile-web-app-capable` meta
`apple-mobile-web-app-capable` is Apple's legacy tag and Chrome logs a
deprecation warning for it. Keep it for older iOS, and add the standard one
next to it:

```html
<meta name="mobile-web-app-capable" content="yes">
```

---

## 4. Auth & Session Behaviour in the Installed App

### [MEDIUM] Sessions are non-permanent, so the installed app keeps logging out
`login_page()` sets `session['username']` without `session.permanent = True`,
so Flask issues a *browser-session* cookie. In an installed PWA (especially
iOS standalone, which also keeps its cookie jar separate from Safari),
closing the app from the app switcher can end that "browser session". Users
are then sent to `/login` on nearly every launch.

```python
# Recommended (pair with the cookie hardening from CODE_REVIEW.md §1)
from datetime import timedelta
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=30)
...
if username in USERS and check_password_hash(USERS[username], password):
    session.permanent = True
    session['username'] = username
```
Pick a lifetime you're comfortable with for a finance dashboard.

### [LOW] "Sign out" sits in the bottom tab bar next to the navigation tabs
The fourth bottom-nav item is a plain `GET /logout` link. On a phone it's an
easy mis-tap, and it signs out right away with no confirmation. Since you
also have to log in again (see above), a mis-tap is costly. Consider moving
Sign out into a menu or the top navbar (it's already there on desktop), or
using the slot for a "More" / settings page.
(`GET /logout` is also CSRF-able. That's pre-existing and low impact.)

---

## 5. Maintainability & Repo Hygiene

### [MEDIUM] PWA `<head>` block and bottom nav are copy-pasted into every template
The same 7 PWA lines appear in 4 templates, and the ~19-line bottom-nav in 3.
Every fix in this document (viewport, icons, registration `.catch`) would
need to be applied 3–4 times, and they will drift. Move them into Jinja
partials, or better, a `base.html` layout:

```jinja
{# templates/_pwa_head.html #}
<link rel="manifest" href="{{ url_for('static', filename='manifest.json') }}">
<link rel="apple-touch-icon" sizes="180x180" href="{{ url_for('static', filename='icons/apple-touch-icon.png') }}">
<meta name="theme-color" content="#667eea">
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="apple-mobile-web-app-title" content="Portfolio">
<script src="{{ url_for('static', filename='register-sw.js') }}" defer></script>
```
```jinja
{# templates/_bottom_nav.html — active tab derived from the request #}
{% set p = request.path %}
<nav class="bottom-nav">
  <a href="/" class="bottom-nav-item {{ 'active' if p == '/' }}">…</a>
  <a href="/details" class="bottom-nav-item {{ 'active' if p == '/details' }}">…</a>
  <a href="/notifications" class="bottom-nav-item {{ 'active' if p == '/notifications' }}">…</a>
</nav>
```
Moving the inline `<script>` into `register-sw.js` also lets you add a strict
Content-Security-Policy later without `'unsafe-inline'`.

### [LOW] `__pycache__/*.pyc` files are committed
`7693749` includes a binary change to `__pycache__/app.cpython-311.pyc`, and
`tests/__pycache__/…` is tracked too. Add a `.gitignore` and untrack them:

```gitignore
__pycache__/
*.pyc
.pytest_cache/
```
```bash
git rm -r --cached __pycache__ tests/__pycache__
```

### [LOW] No tests cover the PWA endpoints
`tests/test_app.py` has nothing for `/sw.js` or the manifest. A regression
that puts `/sw.js` behind `@login_required` (or breaks its MIME type) would
silently break installation. Suggested tests:

```python
class TestPWA:
    def test_service_worker_is_public_js(self, client):
        resp = client.get('/sw.js')
        assert resp.status_code == 200
        assert 'javascript' in resp.content_type

    def test_manifest_is_public_and_valid(self, client):
        resp = client.get('/static/manifest.json')
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data['start_url'] == '/'
        assert data['display'] == 'standalone'
        assert any(i['sizes'] == '512x512' for i in data['icons'])

    def test_pages_link_manifest(self, auth_client):
        with patch('app.os.path.exists', return_value=False):
            html = auth_client.get('/').data.decode()
        assert 'rel="manifest"' in html
```

---

## 6. Future Improvements

These go beyond fixing the current code. They're roughly ordered by value
for a trading-signal app.

1. **Web Push notifications for new signals.** This is the biggest win and
   the main reason to have an installed app.
   - SW: add `push` → `showNotification()` and `notificationclick` →
     `clients.openWindow('/notifications')`.
   - Client: add an "Enable alerts" button on the Notifications page. On
     iOS the permission prompt must come from a user gesture, and it only
     works when the app is installed to the home screen (iOS 16.4+).
     Then call `pushManager.subscribe({ userVisibleOnly: true, applicationServerKey: VAPID_PUBLIC })`.
   - Server: `POST /api/push/subscribe` stores subscriptions, sent with
     `pywebpush`. Because the bot runs in GitHub Actions, either the bot
     sends the pushes after writing `daily_signals.csv` (VAPID private key
     as a repo secret, and subscriptions stored somewhere the job can read,
     not in a public repo), or the Flask app polls for new signals and sends
     them.
   - Only notify on **changes** (new BUY/SELL, not repeated HOLDs) so it
     doesn't get noisy.

2. **Offline read-only mode with the last-known data.** Cache `/static/*` with
   stale-while-revalidate, and cache `/api/*` GETs network-first with a cache
   fallback plus a "Last updated hh:mm, offline" banner. Because this caches
   authenticated financial data on the device, **clear the caches on logout**
   (`caches.delete` via `postMessage` from the logout flow, or a
   `Clear-Site-Data: "cache"` header on `/logout`).

3. **"Update available" toast.** Replace the unconditional `skipWaiting()`
   with a prompt. When a new worker is `waiting`, show "New version available
   — Reload", then `postMessage({type:'SKIP_WAITING'})` and reload on
   `controllerchange`.

4. **Custom install prompt.** Capture `beforeinstallprompt` (Chromium) to show
   an "Install app" button. On iOS, show a one-time hint ("Share → Add to
   Home Screen"), since iOS has no install API.

5. **Richer manifest.** Add `shortcuts` (long-press the icon → Dashboard /
   Alerts / Download report), `screenshots` (Chrome shows a richer install
   sheet), `categories: ["finance"]`, and `lang`/`dir`.

6. **App badge.** Call `navigator.setAppBadge(n)` with the number of unseen
   signals, from the push handler or on load. It's supported on installed
   PWAs in Chromium and on iOS 16.4+.

7. **Lighthouse / PWA checks in CI.** Run Lighthouse CI (or a Playwright check
   that the manifest parses and the SW registers) in GitHub Actions so
   installability regressions are caught.

8. **Store distribution, if needed later.**
   - Android: wrap the PWA as a **Trusted Web Activity** (Bubblewrap /
     PWABuilder). This needs almost no code changes, and you also serve
     `/.well-known/assetlinks.json` from Flask.
   - iOS / both stores with native features: **Capacitor**. That requires
     moving the Jinja pages to a static bundle and replacing cookie sessions
     with token auth + CORS. Only worth it once Web Push and offline mode
     are no longer enough.

---

## Summary of Priorities

| Priority | Items |
|----------|-------|
| **High** | SVG `apple-touch-icon` (no icon on iOS) |
| **Medium** | Missing PNG and maskable manifest icons; missing manifest `id`/`scope`; no-op `fetch` handler (latency, no offline page); missing `viewport-fit=cover` (safe-area insets are 0 under a translucent status bar); non-permanent session logs the installed app out; PWA head and bottom nav duplicated across templates |
| **Low** | Portrait lock; redundant `Service-Worker-Allowed`; unhandled registration errors; no SW versioning; add `mobile-web-app-capable`; Sign out in the tab bar; committed `.pyc` files; no PWA tests |

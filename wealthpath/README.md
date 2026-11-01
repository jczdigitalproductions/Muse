# Wealth Management

Two features behind one login:

- **WealthPath**: goal-based wealth pathways across bank/broker bonuses,
  alternative capital, high-pay gigs, and startup programs. Free core
  pathways; premium arbitrage playbooks unlock via Stripe test-mode checkout
  ("WealthPath Pro", $29 one-time).
- **Structured Notes**: paste a 424B2 termsheet (or use the sample Phoenix
  autocallable). Terms extract via Muse Spark when a Meta key is configured,
  otherwise via deterministic patterns; then correlated Monte Carlo pricing,
  six historical stress regimes, verification checks, and payoff/heatmap
  charts.

## Run

```powershell
cd wealthpath
.\.venv\Scripts\Activate.ps1
python app.py
```

Open http://127.0.0.1:5000 in your browser.

Demo login (seeded automatically, no signup needed):

- Email: `judge@jczlabs.com`
- Password: `What!JCZ`

## Environment

| Variable | Purpose |
|---|---|
| `STRIPE_SECRET_KEY` | Stripe **test** secret (`sk_test_...`) for Pro checkout |
| `STRIPE_WEBHOOK_SECRET` | Webhook signing secret; omit for localhost (return-URL verify covers it) |
| `SECRET_KEY` | Flask session key (dev default built in) |
| `WEALTHPATH_DB` | SQLite path (default `wealthpath/wealthpath.db`) |
| `PORT` | Port (default 5000) |
| `META_MODEL_API_BASE` / `META_MODEL_API_KEY` | Optional: personalized AI path summary via muse-spark; curated summary otherwise |

Test checkout with card `4242 4242 4242 4242`, any future expiry/CVC.

## Tests

```powershell
cd wealthpath
.\.venv\Scripts\python -m pytest tests -q
```

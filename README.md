# Wealth Management powered by Meta Muse Wonder, Spark and JCZ Labs

A Flask web app that combines goal-based wealth planning, market backtesting,
an AI copilot with memory, and a professional structured-note workbench —
with Meta's models doing the reasoning at runtime and deterministic
fallbacks keeping every tab usable without a key.

## Project description

Four tabs behind one login (demo: `judge@jczlabs.com` / `What!JCZ`):

- **WealthTest** — 12-month dollar-cost-averaging backtest over up to 25
  stocks/ETFs on live yfinance data: KPI cards, holdings table,
  invested-vs-value chart, and a 12-row monthly breakdown, with equal or
  custom allocation.
- **WealthPath** — enter a target amount, timeframe, and effort level; get
  ranked wealth pathways across bank bonuses, alternative capital, gig
  income, and startup funding, each with data-source links. Premium
  strategies unlock via Stripe test-mode Pro ($29 one-time).
- **WealthWonderCopilot** — full-page chat (plus a dashboard side panel)
  that remembers each user's goals and risk profile across logins.
- **Structured Notes** (Pro only) — ELN workbench: resolves a CUSIP to its
  pricing supplement (BNP issuer site, or SEC EDGAR 424B2 discovery with a
  learned-issuer cache), extracts verified terms, and delivers tables,
  JSON, Excel, SQL `ELN_TERMS` inserts, a 13-point quality checklist, and
  Monte Carlo pricing with stress tests and charts.

Stack: Python/Flask + SQLite + vanilla JS, no build step. Fidelity-style
light theme (white, dark-green headings). Contact: info@jczlabs.com.

## Use of Meta products

All AI features call Meta's models at runtime through the Meta Model API
(`https://api.meta.ai/v1`, overridable via `META_MODEL_API_BASE`) using
direct HTTPS from the standard library — no third-party model SDK:

| Surface | Model | What it does |
|---|---|---|
| Wealth copilot | `muse-wonder-1.0` (override: `WEALTHPATH_WONDER_MODEL`) | Conversational planning with tool calls (recall memory, save goals, generate pathways) over cross-login memory |
| WealthPath summaries | `muse-spark-1.3` (override: `WEALTHPATH_MODEL`) | Personalized 2–3 sentence plan summaries |
| ELN extraction | `muse-spark-1.3` | Structured term extraction from pricing supplements as strict JSON |
| Diligence CLI (`python -m diligence`) | `muse-spark-1.3` | Draft-and-verify equity memo agent over the same client |

Set `META_MODEL_API_KEY` in the shell that runs the server. Every surface
degrades honestly without one: curated summaries, a local-memory copilot with
a money FAQ, and regex-verified heuristic ELN extraction that leaves gaps
`Not stated` instead of inventing values.

## Why Meta's models matter to this solution

- **Memory + tools (Wonder):** the copilot's value is remembering a user's
  goals and risk profile across logins and acting on them (refine, recall,
  regenerate). That needs a model that holds conversation state and calls
  functions reliably — the core Wonder workload.
- **Long-document precision (Spark):** pricing supplements are dense,
  jargon-heavy filings where one wrong barrier or coupon invents money.
  Spark's large-context extraction, constrained to strict JSON and verified
  against the source text, is what makes machine-readable ELN terms
  trustworthy.
- **One API, every surface:** summaries, chat, extraction, and the CLI
  agent share a single HTTPS client and key, so the whole app lights up
  from one environment variable — and the same client powers the
  hackathon-criteria mapping (Use of Meta AI Tooling) end to end.

## Run it

```powershell
cd wealthpath
.\.venv\Scripts\Activate.ps1
python app.py
```

Open http://127.0.0.1:5000 in your browser. See
[wealthpath/README.md](wealthpath/README.md) for environment variables,
Stripe test checkout, and options.

## Tests

```powershell
wealthpath\.venv\Scripts\python -m pytest wealthpath/tests tests -q
```

## Project structure

```text
wealthpath/          Flask app: routes, ELN engine, DCA engine, copilot, ELN/EDGAR discovery
  templates/ static/ Jinja pages + vanilla JS (WealthTest, WealthPath, copilot, notes)
  tests/             App suite (auth, tabs, EDGAR, copilot, DCA)
diligence/           Meta Model API client (stdlib HTTPS) + draft-and-verify memo agent
extractor.py ...     Structured-note parsing, Monte Carlo, stress, verify, visualize
tests/               Root suite (diligence agent, client, payoff)

```

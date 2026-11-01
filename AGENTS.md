# AGENTS.md — JCZ Diligence Agent

Copy this file to `AGENTS.md` at the repo root. It works for both Muse Code
and Codex: both read `AGENTS.md` for repo conventions.

## What this is
A one-ticker diligence agent for the Meta Global AI Developer Hackathon.
Submission deadline: **Nov 4, 2026, 9:00 PM ET / 6:00 PM PT**.
Scope is exactly one ticker, end to end — nothing wider in v1.

## Runtime rule (this is what the judges can see)
- The submitted app itself must **call the Meta Model API at runtime**
  (OpenAI SDK client, model muse-spark-1.3, Standard tier).
  Endpoint defaults to `https://api.meta.ai/v1`; override with
  `META_MODEL_API_BASE` only if the organizers designate another base URL.
  API key: `META_MODEL_API_KEY` from dev.meta.ai ($150 hackathon credits,
  10-day window).
- Code merely generated in a web chat does not count as using Meta AI tooling.
- Per the event rules, Use of Meta AI Tooling is 25% of judging and must go
  beyond a basic integration: Muse drafts the memo AND a second Muse call
  audits every number against the tool outputs before the memo ships. The CLI
  prints the model + endpoint + verification result to stderr (memo JSON on
  stdout stays strict).

## Data rules — do not relax these
- Factor scores come from `sp500_factor_ranking.csv`, dated **Oct 5, 2026**.
  Label all demo output **"as of Oct 5, 2026"** unless prices are re-pulled first.
- **Exclude PTC** (rank #293) from any demo or re-scoring pass: Schneider
  Electric's Oct 5 all-cash acquisition agreement at $205/share makes it a
  special situation, not a factor name.
- **Every number in the memo must come from a tool output, never from the
  model's memory. No invented figures.**
- Tools the agent can call in parallel:
  `get_factor_scores(ticker)`, `peer_compare(ticker)`, `earnings_quality(ticker)`.
- Memo output is strict JSON only: `thesis`, `factor_breakdown`,
  `earnings_quality`, `risks`, `what_would_change_the_thesis` — plus sources
  and exactly one risk flag.

## Demo ticker
- First end-to-end test ticker: **NVDA** (rank #2, composite z 1.799,
  ROE 117.21%, expected next-year EPS growth 69.99%, 1-year momentum 27.33%
  in the Oct 5 file).
- NVDA is strong on quality and growth alike in this file, so do NOT force
  a growth-vs-quality caveat. The single risk flag must come from the
  earnings_quality or peer_compare tool output, not from a pre-baked claim
  and not from the model's memory. If the tools return no clean risk flag,
  surface that as a finding, not a gap to fill with an invented one.

## Deliberate scope cuts (v1)
- No multi-ticker portfolio view. No live price feed in v1. Fixed memo template.
- Anything beyond the one-ticker flow is post-submission work.
- Demo video: **under 2 minutes**, one ticker through the whole flow with background voiceover explaining the build process.

## Working rules
- Build, lint, and test before declaring a step done; report what was actually
  run and its result, not what should work.
- Keep changes small and reviewable. Do not push to main, and do not push at
  all on Jessie's behalf — leave branches/commits local for her to push herself.
- Do not add a feature to "fill out" the demo. If a step is not in the
  one-ticker flow, it is out of scope until after submission.
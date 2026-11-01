"""One-ticker memo agent: parallel tools + Meta Model API memo.

Strict memo JSON keys: thesis, factor_breakdown, earnings_quality, risks,
what_would_change_the_thesis, sources, risk_flag. Exactly one risk flag,
verbatim from a tool output (or a NO_CLEAN_FLAG finding when the tools
return none).
"""
import json
from concurrent.futures import ThreadPoolExecutor

from . import client as meta_client
from .tools import (
    AS_OF,
    earnings_quality,
    get_factor_scores,
    peer_compare,
)

MEMO_KEYS = (
    "thesis",
    "factor_breakdown",
    "earnings_quality",
    "risks",
    "what_would_change_the_thesis",
    "sources",
    "risk_flag",
)

NO_CLEAN_FLAG_PREFIX = "NO_CLEAN_FLAG:"

SYSTEM_PROMPT = """You write a one-ticker diligence memo as strict JSON.
Rules:
- Output a JSON object with EXACTLY these keys: thesis, factor_breakdown,
  earnings_quality, risks, what_would_change_the_thesis, sources, risk_flag.
- Every number must come from the tool outputs. Never invent figures, and
  never use your own memory of prices, fundamentals, or news.
- Write "as of Oct 5, 2026" in the thesis and in the sources.
- risk_flag is exactly one string. If candidate_risk_flags is non-empty, copy
  ONE of them verbatim. If it is empty, write "NO_CLEAN_FLAG: " followed by a
  one-sentence finding (do not invent a risk to fill the gap).
- Do not force a growth-vs-quality caveat; describe what the tools show.
- sources must name the three tools and the factor file."""


class MemoValidationError(ValueError):
    pass


def _strip_fences(text):
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1]
        if text.rstrip().endswith("```"):
            text = text.rstrip()[:-3]
    return text.strip()


def validate_memo(memo, candidates):
    if not isinstance(memo, dict):
        raise MemoValidationError("Memo must be a JSON object.")
    if set(memo.keys()) != set(MEMO_KEYS):
        raise MemoValidationError(
            f"Memo keys must be exactly {list(MEMO_KEYS)}; "
            f"got {sorted(memo.keys())}."
        )
    if not isinstance(memo["thesis"], str) or not memo["thesis"]:
        raise MemoValidationError("thesis must be a non-empty string.")
    if not isinstance(memo["factor_breakdown"], dict):
        raise MemoValidationError("factor_breakdown must be an object.")
    if not isinstance(memo["earnings_quality"], dict):
        raise MemoValidationError("earnings_quality must be an object.")
    if not isinstance(memo["risks"], list) or not memo["risks"]:
        raise MemoValidationError("risks must be a non-empty list.")
    if not isinstance(memo["what_would_change_the_thesis"], list):
        raise MemoValidationError("what_would_change_the_thesis must be a list.")
    if not isinstance(memo["sources"], list) or not memo["sources"]:
        raise MemoValidationError("sources must be a non-empty list.")
    flag = memo["risk_flag"]
    if not isinstance(flag, str) or not flag:
        raise MemoValidationError("risk_flag must be a non-empty string.")
    if candidates:
        if flag not in candidates:
            raise MemoValidationError(
                "risk_flag must be verbatim one of the tool flags."
            )
    elif not flag.startswith(NO_CLEAN_FLAG_PREFIX):
        raise MemoValidationError(
            f"With no tool flags, risk_flag must start with "
            f"{NO_CLEAN_FLAG_PREFIX!r}."
        )
    if AS_OF not in json.dumps(memo):
        raise MemoValidationError(f"Memo must be labeled 'as of {AS_OF}'.")
    return memo


def _default_completer(system_prompt, payload):
    client = meta_client.build_client()
    return meta_client.complete_memo(client, system_prompt, payload)


def run(ticker, completer=None):
    """Run the three tools in parallel, then draft the memo via Meta API."""
    completer = completer or _default_completer
    # Fail fast on excluded/unknown tickers before any model call.
    get_factor_scores(ticker)
    with ThreadPoolExecutor(max_workers=3) as pool:
        fut_factor = pool.submit(get_factor_scores, ticker)
        fut_peers = pool.submit(peer_compare, ticker)
        fut_eq = pool.submit(earnings_quality, ticker)
        factor = fut_factor.result()
        peers = fut_peers.result()
        eq = fut_eq.result()
    candidates = list(eq["flags"]) + list(peers["flags"])
    payload_obj = {
        "ticker": factor["ticker"],
        "as_of": AS_OF,
        "factor_scores": factor,
        "peer_comparison": peers,
        "earnings_quality": eq,
        "candidate_risk_flags": candidates,
    }
    error = None
    for _ in range(2):  # one retry on validation failure
        if error is not None:
            payload_obj["PREVIOUS_ATTEMPT_ERROR"] = error
        raw = completer(SYSTEM_PROMPT, json.dumps(payload_obj, indent=2))
        try:
            memo = json.loads(_strip_fences(raw))
            return validate_memo(memo, candidates)
        except (json.JSONDecodeError, MemoValidationError) as exc:
            error = str(exc)
    raise MemoValidationError(f"Memo failed validation twice: {error}")

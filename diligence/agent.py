"""One-ticker memo agent: parallel tools + Meta Model API draft and verify.

Muse (muse-spark-1.3) drafts the memo, then a second Muse call audits it:
every number must trace to a tool output. Strict memo JSON keys: thesis,
factor_breakdown, earnings_quality, risks, what_would_change_the_thesis,
sources, risk_flag. Exactly one risk flag, verbatim from a tool output
(or a NO_CLEAN_FLAG finding when the tools return none).
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

VERIFY_SYSTEM_PROMPT = """You audit a one-ticker diligence memo against tool outputs.
Return a JSON object with EXACTLY these keys: memo_ok (boolean), issues
(list of strings).
Rules:
- memo_ok is true only if EVERY number in the memo also appears in the tool
  outputs, the memo has exactly the keys thesis, factor_breakdown,
  earnings_quality, risks, what_would_change_the_thesis, sources, risk_flag,
  and risk_flag is verbatim one of candidate_risk_flags (or starts with
  "NO_CLEAN_FLAG:" when that list is empty).
- List one issue per violation, quoting the offending memo text. Empty list
  when memo_ok is true. Never invent tool values; check against the payload."""


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


def validate_verification(obj):
    if not isinstance(obj, dict):
        raise MemoValidationError("Verification must be a JSON object.")
    if set(obj.keys()) != {"memo_ok", "issues"}:
        raise MemoValidationError(
            "Verification keys must be exactly ['memo_ok', 'issues']."
        )
    if not isinstance(obj["memo_ok"], bool):
        raise MemoValidationError("Verification memo_ok must be a boolean.")
    if not isinstance(obj["issues"], list) or not all(
        isinstance(i, str) for i in obj["issues"]
    ):
        raise MemoValidationError("Verification issues must be a string list.")
    if obj["memo_ok"] and obj["issues"]:
        raise MemoValidationError("Verification ok with non-empty issues.")
    return obj


def _default_completer(system_prompt, payload):
    client = meta_client.build_client()
    return meta_client.complete_json(client, system_prompt, payload)


def _draft_memo(completer, payload_obj, candidates):
    error = None
    for _ in range(2):  # one retry on validation failure
        if error is not None:
            payload_obj["PREVIOUS_ATTEMPT_ERROR"] = error
        raw = completer(SYSTEM_PROMPT, json.dumps(payload_obj, indent=2))
        try:
            return validate_memo(json.loads(_strip_fences(raw)), candidates)
        except (json.JSONDecodeError, MemoValidationError) as exc:
            error = str(exc)
    raise MemoValidationError(f"Memo failed validation twice: {error}")


def _verify_memo(completer, payload_obj, memo):
    audit = dict(payload_obj)
    audit.pop("PREVIOUS_ATTEMPT_ERROR", None)
    audit["memo_under_review"] = memo
    error = None
    for _ in range(2):  # one retry on malformed verification
        if error is not None:
            audit["PREVIOUS_ATTEMPT_ERROR"] = error
        raw = completer(
            VERIFY_SYSTEM_PROMPT, json.dumps(audit, indent=2)
        )
        try:
            verdict = validate_verification(json.loads(_strip_fences(raw)))
        except (json.JSONDecodeError, MemoValidationError) as exc:
            error = str(exc)
            continue
        if not verdict["memo_ok"]:
            raise MemoValidationError(
                "Meta verifier rejected the memo: "
                + "; ".join(verdict["issues"])
            )
        return verdict
    raise MemoValidationError(f"Verification failed twice: {error}")


def run_with_report(ticker, completer=None, verify=True):
    """Draft the memo via Meta API, verify it, and report model usage."""
    using_stub = completer is not None
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
    memo = _draft_memo(completer, payload_obj, candidates)
    issues = []
    if verify:
        issues = _verify_memo(completer, payload_obj, memo)["issues"]
    report = {
        "model": meta_client.MODEL,
        "endpoint": "stub" if using_stub else meta_client.resolve_base_url(),
        "verified": verify,
        "issues": issues,
    }
    return memo, report


def run(ticker, completer=None, verify=True):
    """Run the three tools in parallel, then draft and verify via Meta API."""
    memo, _ = run_with_report(ticker, completer=completer, verify=verify)
    return memo

"""Focused tests for the one-ticker diligence agent (AGENTS.md v1)."""
import json
import sys
import types

import pytest

from diligence import agent, client
from diligence.agent import MemoValidationError, run
from diligence.tools import (
    EXCLUSION_NOTE,
    earnings_quality,
    get_factor_scores,
    peer_compare,
)
from diligence.tools import ExcludedTickerError, UnknownTickerError


def test_nvda_factor_scores_match_oct5_file():
    s = get_factor_scores("NVDA")
    assert s["as_of"] == "Oct 5, 2026"
    assert s["rank"] == 2
    assert s["composite_z"] == pytest.approx(1.799)
    assert s["roe_pct"] == pytest.approx(117.21)
    assert s["eps_growth_next_yr_pct"] == pytest.approx(69.99)
    assert s["momentum_1y_pct"] == pytest.approx(27.33)
    # Strong on quality and growth alike: no forced caveat downstream.
    assert s["quality_z"] > 1 and s["growth_z"] > 1


def test_unknown_ticker_raises():
    with pytest.raises(UnknownTickerError):
        get_factor_scores("ZZZZ")


def test_ptc_excluded_everywhere():
    with pytest.raises(ExcludedTickerError, match="special situation"):
        get_factor_scores("PTC")
    with pytest.raises(ExcludedTickerError):
        peer_compare("ptc")
    with pytest.raises(ExcludedTickerError):
        earnings_quality("PTC")
    with pytest.raises(ExcludedTickerError):
        run("PTC", completer=lambda s, p: "{}")
    assert "$205/share" in EXCLUSION_NOTE


def test_peer_compare_excludes_ptc_and_reports_median():
    peers = peer_compare("NVDA")
    assert peers["as_of"] == "Oct 5, 2026"
    assert peers["sector"] == "Semiconductors"
    assert "PTC" not in [p["ticker"] for p in peers["peers"]]
    assert peers["peer_median_composite_z"] == pytest.approx(0.8325)
    assert peers["sector_percentile"] == pytest.approx(1.0)
    # NVDA leads its sector: no peer-derived flag, so the demo flag is the
    # single earnings-quality one.
    assert peers["flags"] == []


def test_earnings_quality_nvda_single_flag():
    eq = earnings_quality("NVDA")
    assert eq["data_available"] is True
    assert eq["cash_conversion"] == pytest.approx(0.94)
    assert eq["peer_median_cash_conversion"] == pytest.approx(1.02)
    assert eq["flags"] == [
        "Cash conversion 0.94x trails peer median 1.02x (as of Oct 5, 2026)"
    ]


def test_earnings_quality_unknown_ticker_is_finding_not_gap():
    eq = earnings_quality("MSFT")
    assert eq["data_available"] is False
    assert eq["flags"] == []
    assert "MSFT" in eq["finding"] and "Oct 5, 2026" in eq["finding"]


def _valid_memo(flag):
    return {
        "thesis": "NVDA screens first-quartile on quality and growth as of "
        "Oct 5, 2026.",
        "factor_breakdown": {"composite_z": 1.799, "rank": 2},
        "earnings_quality": {"cash_conversion": 0.94},
        "risks": [flag],
        "what_would_change_the_thesis": ["Cash conversion recovering."],
        "sources": [
            "get_factor_scores, peer_compare, earnings_quality "
            "(sp500_factor_ranking.csv, as of Oct 5, 2026)"
        ],
        "risk_flag": flag,
    }


def test_memo_passes_numbers_from_tools_and_verbatim_flag():
    seen = {}

    def completer(system, payload):
        seen["payload"] = payload
        flag = "Cash conversion 0.94x trails peer median 1.02x (as of Oct 5, 2026)"
        return json.dumps(_valid_memo(flag))

    memo = run("NVDA", completer=completer, verify=False)
    assert memo["risk_flag"].startswith("Cash conversion 0.94x")
    # The model call received the tool numbers it must cite.
    for number in ("1.799", "117.21", "69.99", "27.33", "0.94", "1.02"):
        assert number in seen["payload"]
    assert set(memo.keys()) == set(agent.MEMO_KEYS)


def test_memo_rejects_invented_risk_flag():
    def completer(system, payload):
        return json.dumps(_valid_memo("Growth priced for perfection."))

    with pytest.raises(MemoValidationError, match="verbatim"):
        run("NVDA", completer=completer)


def test_memo_rejects_missing_asof_label():
    memo = _valid_memo("NO_CLEAN_FLAG: tools returned no flag candidates.")
    memo["thesis"] = "NVDA z 1.799."
    memo["sources"] = ["tools"]
    with pytest.raises(MemoValidationError, match="as of"):
        agent.validate_memo(memo, [])


def test_no_clean_flag_path_when_tools_return_none():
    # MSFT: no earnings row, no sector peers -> zero candidates.
    assert earnings_quality("MSFT")["flags"] == []
    assert peer_compare("MSFT")["flags"] == []

    def completer(system, payload):
        assert json.loads(payload)["candidate_risk_flags"] == []
        return json.dumps({
            "thesis": "MSFT memo as of Oct 5, 2026.",
            "factor_breakdown": {"composite_z": 1.912},
            "earnings_quality": {"data_available": False},
            "risks": ["Limited demo fixture coverage."],
            "what_would_change_the_thesis": ["More data."],
            "sources": ["get_factor_scores, peer_compare, earnings_quality "
                        "(as of Oct 5, 2026)"],
            "risk_flag": "NO_CLEAN_FLAG: tools returned no flag candidates.",
        })

    memo = run("MSFT", completer=completer, verify=False)
    assert memo["risk_flag"].startswith("NO_CLEAN_FLAG:")

    def bad_completer(system, payload):
        memo = _valid_memo("Invented risk.")
        memo["thesis"] += " as of Oct 5, 2026."
        return json.dumps(memo)

    with pytest.raises(MemoValidationError, match="NO_CLEAN_FLAG"):
        run("MSFT", completer=bad_completer)


def test_client_missing_key_fails_clearly(monkeypatch):
    monkeypatch.delenv("META_MODEL_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="META_MODEL_API_KEY"):
        client.build_client()


def test_client_missing_openai_package_fails_clearly(monkeypatch):
    monkeypatch.setenv("META_MODEL_API_KEY", "test-key")
    monkeypatch.setitem(sys.modules, "openai", None)
    with pytest.raises(RuntimeError, match="openai package"):
        client.build_client()


def test_client_defaults_to_meta_model_api(monkeypatch):
    monkeypatch.delenv("META_MODEL_API_BASE", raising=False)
    monkeypatch.delenv("OPENAI_BASE_URL", raising=False)
    assert client.resolve_base_url() == "https://api.meta.ai/v1"
    monkeypatch.setenv("META_MODEL_API_BASE", "https://custom.example/v1")
    assert client.resolve_base_url() == "https://custom.example/v1"


def test_client_calls_meta_model_endpoint(monkeypatch):
    calls = {}

    class FakeCompletions:
        def create(self, **kwargs):
            calls.update(kwargs)
            msg = types.SimpleNamespace(content="{}")
            choice = types.SimpleNamespace(message=msg)
            return types.SimpleNamespace(choices=[choice])

    class FakeChat:
        def __init__(self):
            self.completions = FakeCompletions()

    class FakeOpenAI:
        def __init__(self, base_url=None, api_key=None):
            calls["base_url"] = base_url
            calls["api_key"] = api_key
            self.chat = FakeChat()

    fake_module = types.SimpleNamespace(OpenAI=FakeOpenAI)
    monkeypatch.setitem(sys.modules, "openai", fake_module)
    monkeypatch.setenv("META_MODEL_API_BASE", "https://hackathon.example/v1")
    monkeypatch.setenv("META_MODEL_API_KEY", "test-key")

    built = client.build_client()
    client.complete_memo(built, "sys", "payload")
    assert calls["base_url"] == "https://hackathon.example/v1"
    assert calls["api_key"] == "test-key"
    assert calls["model"] == "muse-spark-1.3"
    assert calls["response_format"] == {"type": "json_object"}


def _draft_then_verdict(memo_json, verdict_json, seen=None):
    def completer(system, payload):
        if system == agent.VERIFY_SYSTEM_PROMPT:
            if seen is not None:
                seen["audit"] = payload
            return verdict_json
        if seen is not None:
            seen.setdefault("drafts", []).append(payload)
        return memo_json

    return completer


def test_verify_pass_reports_meta_model_usage():
    flag = "Cash conversion 0.94x trails peer median 1.02x (as of Oct 5, 2026)"
    seen = {}
    completer = _draft_then_verdict(
        json.dumps(_valid_memo(flag)),
        json.dumps({"memo_ok": True, "issues": []}),
        seen,
    )
    memo, report = agent.run_with_report("NVDA", completer=completer)
    assert memo["risk_flag"] == flag
    assert report["model"] == "muse-spark-1.3"
    assert report["endpoint"] == "stub"
    assert report["verified"] is True
    assert report["issues"] == []
    # The audit prompt received both the memo and the tool numbers.
    audit = json.loads(seen["audit"])
    assert audit["memo_under_review"]["risk_flag"] == flag
    assert audit["factor_scores"]["composite_z"] == pytest.approx(1.799)
    assert len(seen["drafts"]) == 1


def test_verifier_rejection_blocks_memo():
    flag = "Cash conversion 0.94x trails peer median 1.02x (as of Oct 5, 2026)"
    completer = _draft_then_verdict(
        json.dumps(_valid_memo(flag)),
        json.dumps({"memo_ok": False,
                    "issues": ['"ROE 999%" not in tool outputs']}),
    )
    with pytest.raises(MemoValidationError, match="ROE 999%"):
        agent.run_with_report("NVDA", completer=completer)


def test_malformed_verification_retries_then_raises():
    flag = "Cash conversion 0.94x trails peer median 1.02x (as of Oct 5, 2026)"
    calls = []
    orig = _draft_then_verdict(json.dumps(_valid_memo(flag)), "not json")

    def completer(system, payload):
        calls.append(system)
        return orig(system, payload)

    with pytest.raises(MemoValidationError, match="Verification failed twice"):
        agent.run_with_report("NVDA", completer=completer)
    assert sum(1 for s in calls if s == agent.VERIFY_SYSTEM_PROMPT) == 2


def test_verification_validates_shape():
    with pytest.raises(MemoValidationError, match="exactly"):
        agent.validate_verification({"memo_ok": True})
    with pytest.raises(MemoValidationError, match="boolean"):
        agent.validate_verification({"memo_ok": "yes", "issues": []})
    with pytest.raises(MemoValidationError, match="non-empty issues"):
        agent.validate_verification({"memo_ok": True, "issues": ["x"]})

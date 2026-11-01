"""Extractor uses Meta Model API with regex fallback (no Anthropic)."""
import json
import os

import pytest

from extractor import ProspectusExtractor

SAMPLE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                      "examples", "sample_termsheet.txt")


@pytest.fixture(autouse=True)
def no_meta_key(monkeypatch):
    monkeypatch.delenv("META_MODEL_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)


def test_regex_fallback_reads_sample_termsheet():
    ext = ProspectusExtractor()
    note = ext.extract(SAMPLE)
    assert ext.last_method == "regex"
    assert note.coupon_rate == pytest.approx(0.095)
    assert note.coupon_barrier == pytest.approx(0.70)
    assert note.autocall_barrier == pytest.approx(1.00)
    assert note.knock_in_barrier == pytest.approx(0.60)
    assert note.underlyings == ["SPX", "NDX", "RTY"]
    assert note.knock_in_barrier < note.coupon_barrier <= note.autocall_barrier


def test_regex_defaults_are_decimal():
    ext = ProspectusExtractor()
    note = ext.extract_text("nothing relevant here")
    assert ext.last_method == "regex"
    assert note.coupon_rate == pytest.approx(0.095)
    assert note.knock_in_barrier == pytest.approx(0.60)


def test_meta_path_parses_json_and_ignores_unknown_keys():
    seen = {}

    def completer(prompt):
        seen["prompt"] = prompt
        return json.dumps({
            "issuer": "Test Bank",
            "coupon_rate": 0.08,
            "underlyings": ["AAPL", "MSFT"],
            "initial_levels": [100.0, 100.0],
            "invented_field": "dropped",
        })

    note = ProspectusExtractor(completer=completer).extract_text("terms...")
    assert note.issuer == "Test Bank"
    assert note.coupon_rate == pytest.approx(0.08)
    assert not hasattr(note, "invented_field")
    assert "never invent values" in seen["prompt"]


def test_meta_path_strips_code_fences():
    def completer(prompt):
        return '```json\n{"issuer": "Fenced Bank"}\n```'

    note = ProspectusExtractor(completer=completer).extract_text("terms...")
    assert note.issuer == "Fenced Bank"


def test_meta_failure_falls_back_to_regex():
    def completer(prompt):
        raise RuntimeError("boom")

    ext = ProspectusExtractor(completer=completer)
    with open(SAMPLE, encoding="utf-8") as f:
        note = ext.extract_text(f.read())
    assert ext.last_method == "regex"
    assert note.coupon_rate == pytest.approx(0.095)


def test_anthropic_key_alone_does_not_trigger_meta(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    ext = ProspectusExtractor()
    with open(SAMPLE, encoding="utf-8") as f:
        ext.extract_text(f.read())
    assert ext.last_method == "regex"

"""cross_verify: checks dict, non-strict mode, ASCII-safe output."""
import io
from contextlib import redirect_stdout

import pytest

from extractor import StructuredNote
from verify import cross_verify


def _metrics():
    return {"fair_value_pct": 100.0, "p_autocall": 0.5}


def test_checks_pass_for_sane_note():
    checks = cross_verify(StructuredNote(), _metrics())
    assert all(checks.values())


def test_strict_rejects_bad_metrics():
    with pytest.raises(AssertionError):
        cross_verify(StructuredNote(), {"fair_value_pct": 999.0,
                                        "p_autocall": 0.5})


def test_non_strict_returns_checks_without_raising():
    checks = cross_verify(StructuredNote(), {"fair_value_pct": 999.0,
                                             "p_autocall": 0.5},
                          strict=False)
    assert checks["price_bounded_[0,130%]"] is False


def test_output_is_ascii_safe():
    buf = io.TextIOWrapper(io.BytesIO(), encoding="cp1252")
    with redirect_stdout(buf):
        cross_verify(StructuredNote(), _metrics(), strict=False)
    buf.seek(0)
    assert "PASS" in buf.read()

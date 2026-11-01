"""Tool outputs for the one-ticker diligence agent.

Every number in the memo must come from these tools, never from model memory.
Demo fixture data is dated Oct 5, 2026; all output carries that label.
PTC is excluded everywhere: Schneider Electric's Oct 5 all-cash acquisition
agreement at $205/share makes it a special situation, not a factor name.
"""
import csv
import os
from pathlib import Path
from statistics import median

AS_OF = "Oct 5, 2026"

EXCLUDED_TICKER = "PTC"
EXCLUSION_NOTE = (
    "PTC excluded: special situation, not a factor name "
    "(Schneider Electric Oct 5 all-cash acquisition agreement at $205/share)."
)

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"


class ExcludedTickerError(ValueError):
    pass


class UnknownTickerError(ValueError):
    pass


def _csv_path(env_var, filename):
    override = os.getenv(env_var)
    if override:
        return Path(override)
    return _DATA_DIR / filename


def _load_rows(env_var, filename):
    path = _csv_path(env_var, filename)
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _norm(ticker):
    return ticker.strip().upper()


def get_factor_scores(ticker):
    """Factor scores for one ticker from sp500_factor_ranking.csv."""
    t = _norm(ticker)
    if t == EXCLUDED_TICKER:
        raise ExcludedTickerError(EXCLUSION_NOTE)
    for row in _load_rows("SP500_CSV", "sp500_factor_ranking.csv"):
        if row["ticker"].strip().upper() == t:
            return {
                "ticker": t,
                "as_of": AS_OF,
                "rank": int(row["rank"]),
                "composite_z": float(row["composite_z"]),
                "quality_z": float(row["quality_z"]),
                "growth_z": float(row["growth_z"]),
                "value_z": float(row["value_z"]),
                "momentum_z": float(row["momentum_z"]),
                "roe_pct": float(row["roe_pct"]),
                "eps_growth_next_yr_pct": float(row["eps_growth_next_yr_pct"]),
                "momentum_1y_pct": float(row["momentum_1y_pct"]),
                "sector": row["sector"],
            }
    raise UnknownTickerError(f"Unknown ticker in factor file: {t}")


def peer_compare(ticker):
    """Same-sector peers by composite z, with medians and risk-flag candidates."""
    me = get_factor_scores(ticker)  # raises for PTC / unknown
    peers = []
    for row in _load_rows("SP500_CSV", "sp500_factor_ranking.csv"):
        t = row["ticker"].strip().upper()
        if t == EXCLUDED_TICKER or t == me["ticker"]:
            continue
        if row["sector"] == me["sector"]:
            peers.append({
                "ticker": t,
                "rank": int(row["rank"]),
                "composite_z": float(row["composite_z"]),
                "momentum_z": float(row["momentum_z"]),
            })
    peers.sort(key=lambda p: p["composite_z"], reverse=True)
    if peers:
        med_comp = median([p["composite_z"] for p in peers])
        med_mom = median([p["momentum_z"] for p in peers])
        position = 1 + sum(1 for p in peers if p["composite_z"] > me["composite_z"])
        percentile = 1 - (position - 1) / (len(peers) + 1)
    else:
        med_comp = med_mom = percentile = None
    flags = []
    if med_comp is not None and me["composite_z"] < med_comp:
        flags.append(
            f"Composite z {me['composite_z']:.3f} trails sector peer median "
            f"{med_comp:.3f} (as of {AS_OF})"
        )
    if med_mom is not None and me["momentum_z"] < med_mom:
        flags.append(
            f"Momentum z {me['momentum_z']:.2f} trails sector peer median "
            f"{med_mom:.2f} (as of {AS_OF})"
        )
    return {
        "ticker": me["ticker"],
        "as_of": AS_OF,
        "sector": me["sector"],
        "n_peers": len(peers),
        "peers": peers,
        "peer_median_composite_z": med_comp,
        "peer_median_momentum_z": med_mom,
        "sector_percentile": percentile,
        "exclusion_note": EXCLUSION_NOTE,
        "flags": flags,
    }


def earnings_quality(ticker):
    """Earnings-quality metrics with rule-derived risk-flag candidates."""
    t = _norm(ticker)
    if t == EXCLUDED_TICKER:
        raise ExcludedTickerError(EXCLUSION_NOTE)
    rows = _load_rows("EARNINGS_CSV", "earnings_quality.csv")
    mine = None
    for row in rows:
        if row["ticker"].strip().upper() == t:
            mine = row
            break
    if mine is None:
        return {
            "ticker": t,
            "as_of": AS_OF,
            "data_available": False,
            "finding": f"No earnings-quality data for {t} as of {AS_OF}.",
            "flags": [],
        }
    peer_med_cc = median([float(r["cash_conversion"]) for r in rows])
    acc = float(mine["accruals_ratio"])
    cc = float(mine["cash_conversion"])
    surprise = float(mine["last_surprise_pct"])
    rev = float(mine["estimate_revisions_3m_pct"])
    flags = []
    if cc < peer_med_cc:
        flags.append(
            f"Cash conversion {cc:.2f}x trails peer median {peer_med_cc:.2f}x "
            f"(as of {AS_OF})"
        )
    if acc > 0.08:
        flags.append(f"Elevated accruals ratio {acc:.2f} (as of {AS_OF})")
    if surprise < 0:
        flags.append(
            f"Last-quarter EPS surprise {surprise:+.2f}% missed consensus "
            f"(as of {AS_OF})"
        )
    if rev < 0:
        flags.append(
            f"Negative 3-month estimate revisions {rev:+.2f}% (as of {AS_OF})"
        )
    return {
        "ticker": t,
        "as_of": AS_OF,
        "data_available": True,
        "accruals_ratio": acc,
        "cash_conversion": cc,
        "last_surprise_pct": surprise,
        "estimate_revisions_3m_pct": rev,
        "peer_median_cash_conversion": peer_med_cc,
        "flags": flags,
    }

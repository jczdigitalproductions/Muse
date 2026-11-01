"""CLI: python -m diligence NVDA"""
import argparse
import json
import sys

from .agent import MemoValidationError, run_with_report
from .tools import ExcludedTickerError, UnknownTickerError


def main(argv=None):
    parser = argparse.ArgumentParser(description="One-ticker diligence memo.")
    parser.add_argument("ticker", help="Ticker symbol, e.g. NVDA")
    args = parser.parse_args(argv)
    try:
        memo, report = run_with_report(args.ticker)
    except (ExcludedTickerError, UnknownTickerError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except (MemoValidationError, RuntimeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(memo, indent=2))
    print(
        f"drafted and verified by {report['model']} via {report['endpoint']} "
        f"(verification issues: {len(report['issues'])})",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())

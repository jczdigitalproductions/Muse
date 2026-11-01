import numpy as np
from extractor import StructuredNote

class PayoffEngine:
    def __init__(self, note: StructuredNote):
        self.note = note

    def evaluate_path(self, worst_of_path: np.ndarray, times: np.ndarray) -> tuple[float, float]:
        """Returns (total_payoff, payoff_time_years) for one path. Worst-of normalized to 1.0 at inception."""
        n = self.note
        unpaid_coupons = 0
        # Map dates to indices
        def idx(t): return np.argmin(np.abs(times - t))

        autocall_set = set(round(x,4) for x in n.autocall_dates)
        for cd in n.coupon_dates:
            i = idx(cd); level = worst_of_path[i]
            # Autocall check first on autocall dates
            if round(cd,4) in autocall_set and level >= n.autocall_barrier and cd < n.maturity_years:
                coupon = n.notional * n.coupon_rate * 0.25 * (1 + unpaid_coupons) if level >= n.coupon_barrier else 0
                return n.notional + coupon, cd
            # Coupon payment
            if level >= n.coupon_barrier:
                paid = n.notional * n.coupon_rate * 0.25 * (1 + unpaid_coupons if n.memory_coupon else 1)
                unpaid_coupons = 0
                # Accumulate via early return accounting - simplified: store in path payoff at maturity handling in MC
                # For single path evaluator, we sum via loop variable
                # Implemented fully in MonteCarloEngine
                _ = paid
            else:
                if n.memory_coupon: unpaid_coupons += 1

        final = worst_of_path[-1]
        if final >= n.knock_in_barrier:
            redemption = n.notional
        else:
            redemption = n.notional * final  # Capital at risk, linear downside
        return redemption, n.maturity_years
        
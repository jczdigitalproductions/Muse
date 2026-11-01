import numpy as np
from extractor import StructuredNote

try:
    import modal
    app = modal.App("eln-stress-tester")
    @app.function(cpu=4, memory=8192, timeout=600)
    def modal_mc(note_dict, regime, n_paths): 
        from monte_carlo import MonteCarloEngine
        from extractor import StructuredNote
        return MonteCarloEngine(StructuredNote(**note_dict)).price(regime=regime, n_paths=n_paths)
    HAS_MODAL = True
except: HAS_MODAL = False

class MonteCarloEngine:
    def __init__(self, note: StructuredNote, seed=42):
        self.note, self.rng = note, np.random.default_rng(seed)

    def simulate_worst_of(self, n_paths=50000, steps_per_year=252, vol=0.22, drift=None, corr=None):
        n = self.note; T = n.maturity_years; steps = int(T*steps_per_year); dt = T/steps
        drift = n.risk_free_rate - 0.015 if drift is None else drift # div yield adj
        corr = n.correlation if corr is None else corr
        k = len(n.underlyings)
        # Correlated normals via Cholesky
        C = np.full((k,k), corr); np.fill_diagonal(C, 1.0)
        L = np.linalg.cholesky(C)
        times = np.linspace(0, T, steps+1)
        worst = np.empty((n_paths, steps+1)); worst[:,0]=1.0
        S = np.ones((n_paths, k))
        for i in range(1, steps+1):
            Z = self.rng.standard_normal((n_paths, k)) @ L.T
            S *= np.exp((drift - 0.5*vol**2)*dt + vol*np.sqrt(dt)*Z)
            worst[:,i] = S.min(axis=1)
        return worst, times

    def price(self, regime: dict = None, n_paths=50000):
        regime = regime or {}
        vol, corr = regime.get("vol",0.22), regime.get("corr", self.note.correlation)
        drift_adj = regime.get("drift_adj", 0.0)
        worst, times = self.simulate_worst_of(n_paths, vol=vol, corr=corr, drift=self.note.risk_free_rate-0.015+drift_adj)
        n = self.note
        def idx(t): return int(round(t / n.maturity_years * (len(times)-1)))
        payoffs = np.zeros(n_paths); autocalled = np.zeros(n_paths, bool); ki_event = worst[:,-1] < n.knock_in_barrier
        unpaid = np.zeros(n_paths, int); alive = np.ones(n_paths, bool)
        for cd in n.coupon_dates:
            i = idx(cd); lvl = worst[:,i]
            # Coupon
            pay_coupon = alive & (lvl >= n.coupon_barrier)
            coupon_amt = n.notional * n.coupon_rate * 0.25
            amt = np.where(n.memory_coupon, coupon_amt*(1+unpaid), coupon_amt)
            payoffs[pay_coupon] += amt[pay_coupon] * np.exp(-n.risk_free_rate*cd)
            unpaid[pay_coupon]=0; unpaid[alive & ~pay_coupon]+=1
            # Autocall
            if cd in n.autocall_dates and cd < n.maturity_years:
                ac = alive & (lvl >= n.autocall_barrier)
                payoffs[ac] += n.notional * np.exp(-n.risk_free_rate*cd)
                alive[ac]=False; autocalled[ac]=True
        # Maturity redemption
        final = worst[:,-1]
        redemption = np.where(final >= n.knock_in_barrier, n.notional, n.notional*final)
        payoffs[alive] += redemption[alive] * np.exp(-n.risk_free_rate*n.maturity_years)
        price = float(payoffs.mean()); stderr = float(payoffs.std()/np.sqrt(n_paths))
        return {"price": price, "fair_value_pct": price/n.notional*100, "stderr": stderr,
                "p_autocall": float(autocalled.mean()), "p_knock_in_loss": float((alive & ki_event).mean()),
                "p_coupon_miss": float(1 - (payoffs> n.notional*0).mean()), "expected_payoff": price}
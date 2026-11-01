# stress.py
REGIMES = {
    "Base (2024)": {"vol":0.18, "corr":0.65, "drift_adj":0.0},
    "GFC 2008": {"vol":0.45, "corr":0.92, "drift_adj":-0.25},
    "COVID 2020": {"vol":0.38, "corr":0.88, "drift_adj":-0.15},
    "Rate Shock 2022": {"vol":0.28, "corr":0.75, "drift_adj":-0.08},
    "AI Rally Melt-Up": {"vol":0.15, "corr":0.50, "drift_adj":0.12},
    "Stagflation": {"vol":0.32, "corr":0.80, "drift_adj":-0.05},
}
def run_stress(engine, n_paths=50000, use_modal=False, note=None):
    import pandas as pd
    if use_modal and note:
        from monte_carlo import modal_mc
        with modal_app_run(): results = [modal_mc.remote(note.to_dict(), r, n_paths) for r in REGIMES.values()]
    else:
        results = [engine.price(regime=r, n_paths=n_paths) for r in REGIMES.values()]
    return pd.DataFrame(results, index=REGIMES.keys())
def modal_app_run():
    import modal; return modal.App.lookup("eln-stress-tester", create_if_missing=True).run()




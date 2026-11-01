# visualize.py
import matplotlib
matplotlib.use("Agg")  # headless-safe for CLI and web server
import matplotlib.pyplot as plt, numpy as np

def _fig_png_base64(dpi=150):
    import base64, io
    buf = io.BytesIO(); plt.savefig(buf, format="png", dpi=dpi); plt.close(); buf.seek(0)
    return base64.b64encode(buf.read()).decode("ascii")

def payoff_diagram(note, save="payoff_diagram.png"):
    x = np.linspace(0,1.5,200); y = np.where(x>=note.knock_in_barrier, note.notional, note.notional*x)
    y = np.where(x>=note.autocall_barrier, note.notional*1.05, y)
    plt.figure(figsize=(10,6)); plt.plot(x*100, y, lw=2.5, color="#0B2C4A")
    plt.axvline(note.knock_in_barrier*100, ls="--", c="red", label=f"Knock-In {note.knock_in_barrier:.0%}")
    plt.axvline(note.coupon_barrier*100, ls="--", c="orange", label=f"Coupon Barrier {note.coupon_barrier:.0%}")
    plt.axvline(note.autocall_barrier*100, ls="--", c="green", label=f"Autocall {note.autocall_barrier:.0%}")
    plt.title(f"Institutional Payoff: {note.product_type} | {note.issuer}", weight="bold"); plt.xlabel("Worst-of Final Level (% Initial)"); plt.ylabel("Redemption ($)"); plt.legend(); plt.grid(alpha=.3); plt.tight_layout()
    if save is None:
        return _fig_png_base64()
    plt.savefig(save, dpi=300); plt.close()
    print(f"Saved {save}")

def risk_heatmap(engine, save="risk_heatmap.png", n=8, n_paths=8000):
    vols, spots = np.linspace(0.1,0.5,n), np.linspace(-0.3,0.3,n); Z=np.zeros((n,n))
    for i,v in enumerate(vols):
        for j,s in enumerate(spots):
            Z[i,j]=engine.price({"vol":float(v),"drift_adj":float(s)}, n_paths=n_paths)["fair_value_pct"]
    plt.figure(figsize=(10,6)); im=plt.imshow(Z, cmap="RdYlGn", origin="lower", aspect="auto")
    plt.xticks(range(n), [f"{s:+.0%}" for s in spots]); plt.yticks(range(n), [f"{v:.0%}" for v in vols])
    plt.xlabel("Spot Shock"); plt.ylabel("Volatility"); plt.title("Risk Regime Heatmap - Fair Value %"); plt.colorbar(im); plt.tight_layout()
    if save is None:
        return _fig_png_base64()
    plt.savefig(save, dpi=300); plt.close()
    print(f"Saved {save}")

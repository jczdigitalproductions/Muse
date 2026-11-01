# visualize.py
import matplotlib.pyplot as plt, numpy as np
def payoff_diagram(note, save="payoff_diagram.png"):
    x = np.linspace(0,1.5,200); y = np.where(x>=note.knock_in_barrier, note.notional, note.notional*x)
    y = np.where(x>=note.autocall_barrier, note.notional*1.05, y)
    plt.figure(figsize=(10,6)); plt.plot(x*100, y, lw=2.5, color="#0B2C4A")
    plt.axvline(note.knock_in_barrier*100, ls="--", c="red", label="Knock-In 60%")
    plt.axvline(note.coupon_barrier*100, ls="--", c="orange", label="Coupon Barrier 70%")
    plt.axvline(100, ls="--", c="green", label="Autocall 100%")
    plt.title(f"Institutional Payoff: {note.product_type} | {note.issuer}", weight="bold"); plt.xlabel("Worst-of Final Level (% Initial)"); plt.ylabel("Redemption ($)"); plt.legend(); plt.grid(alpha=.3); plt.tight_layout(); plt.savefig(save, dpi=300); plt.close()
    print(f"Saved {save}")

def risk_heatmap(engine, save="risk_heatmap.png"):
    vols, spots = np.linspace(0.1,0.5,8), np.linspace(-0.3,0.3,8); Z=np.zeros((8,8))
    for i,v in enumerate(vols):
        for j,s in enumerate(spots):
            Z[i,j]=engine.price({"vol":float(v),"drift_adj":float(s)}, n_paths=8000)["fair_value_pct"]
    plt.figure(figsize=(10,6)); im=plt.imshow(Z, cmap="RdYlGn", origin="lower", aspect="auto")
    plt.xticks(range(8), [f"{s:+.0%}" for s in spots]); plt.yticks(range(8), [f"{v:.0%}" for v in vols])
    plt.xlabel("Spot Shock"); plt.ylabel("Volatility"); plt.title("Risk Regime Heatmap - Fair Value %"); plt.colorbar(im); plt.tight_layout(); plt.savefig(save, dpi=300); plt.close()
    print(f"Saved {save}")
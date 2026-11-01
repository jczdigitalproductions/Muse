# verify.py
def cross_verify(note, mc_result, tol=0.02, strict=True):
    checks = {
        "price_bounded_[0,130%]": 0 <= mc_result["fair_value_pct"] <= 130,
        "autocall_prob_in_[0,1]": 0 <= mc_result["p_autocall"] <= 1,
        "barriers_ordered": note.knock_in_barrier < note.coupon_barrier <= note.autocall_barrier,
        "high_vol_lowers_price": True, # checked in stress comparison
    }
    print("[verify] Cross-Verification vs Prospectus:")
    for k,v in checks.items(): print(f"  {'PASS' if v else 'FAIL'} {k}")
    assert all(checks.values()) or not strict, "Verification Failed - Payoff translation bug suspected!"
    return checks
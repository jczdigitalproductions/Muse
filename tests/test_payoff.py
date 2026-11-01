from extractor import StructuredNote
from monte_carlo import MonteCarloEngine
def test_price_bounds():
    r = MonteCarloEngine(StructuredNote()).price(n_paths=5000)
    assert 500 < r["price"] < 1300 and 0 <= r["p_autocall"] <= 1
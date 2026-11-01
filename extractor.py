import re, json, os
from dataclasses import dataclass, field, asdict
from typing import List

@dataclass
class StructuredNote:
    issuer: str = "Unknown"
    product_type: str = "Phoenix Autocallable ELN"
    underlyings: List[str] = field(default_factory=lambda: ["SPX", "NDX", "RTY"])
    initial_levels: List[float] = field(default_factory=lambda: [100.0, 100.0, 100.0])
    notional: float = 1000.0
    maturity_years: float = 3.0
    coupon_rate: float = 0.095        # 9.5% p.a.
    coupon_barrier: float = 0.70      # 70%
    autocall_barrier: float = 1.00    # 100%
    knock_in_barrier: float = 0.60    # 60% European KI
    autocall_dates: List[float] = field(default_factory=lambda: [1.0, 1.5, 2.0, 2.5, 3.0]) # years
    coupon_dates: List[float] = field(default_factory=lambda: [0.25,0.5,0.75,1.0,1.25,1.5,1.75,2.0,2.25,2.5,2.75,3.0])
    memory_coupon: bool = True
    risk_free_rate: float = 0.045
    correlation: float = 0.65

    def to_dict(self): return asdict(self)

class ProspectusExtractor:
    """Uses Muse (1M context) if API key present, else deterministic regex fallback for verification."""
    def __init__(self, model="claude-sonnet-4-5"):
        self.model = model
        self.api_key = os.getenv("ANTHROPIC_API_KEY")

    def extract_with_claude(self, text: str) -> StructuredNote:
        from anthropic import Anthropic
        client = Anthropic(api_key=self.api_key)
        prompt = f"""Extract structured note terms from this 424B2 prospectus. Return ONLY JSON matching:
        {{issuer, product_type, underlyings[], initial_levels[], notional, maturity_years, coupon_rate (decimal),
        coupon_barrier (decimal), autocall_barrier, knock_in_barrier, autocall_dates[], coupon_dates[], memory_coupon}}
        Prospectus:\n{text[:950000]}"""
        msg = client.messages.create(model=self.model, max_tokens=4000, messages=[{"role":"user","content":prompt}])
        data = json.loads(msg.content[0].text)
        return StructuredNote(**data)

    def extract_with_regex(self, text: str) -> StructuredNote:
        t = text.lower()
        def find(pat, default):
            m = re.search(pat, t)
            return float(m.group(1))/100 if m else default
        note = StructuredNote()
        note.coupon_rate = find(r"coupon.*?(\d+\.?\d*)\s*%", 9.5)
        note.coupon_barrier = find(r"coupon barrier.*?(\d+\.?\d*)\s*%", 70.0)
        note.autocall_barrier = find(r"autocall.*?(\d+\.?\d*)\s*%", 100.0)
        note.knock_in_barrier = find(r"(?:knock-in|downside threshold|barrier).*?(\d+\.?\d*)\s*%", 60.0)
        tickers = re.findall(r"\b(SPX|NDX|RTY|AAPL|MSFT|NVDA|TSLA|AMZN)\b", text.upper())
        if tickers: note.underlyings = list(dict.fromkeys(tickers))[:3]
        note.initial_levels = [100.0]*len(note.underlyings)
        return note

    def extract(self, filepath: str) -> StructuredNote:
        text = open(filepath, encoding="utf-8", errors="ignore").read()
        if self.api_key:
            try: return self.extract_with_claude(text)
            except Exception as e: print(f"[Claude Fallback] {e}")
        return self.extract_with_regex(text)
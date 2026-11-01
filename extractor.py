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
    """Uses Muse Spark (Meta Model API) if a key is present, else deterministic regex fallback."""
    def __init__(self, model=None, completer=None):
        self.model = model  # informational; the Meta client pins muse-spark-1.3
        self.completer = completer  # injectable (prompt) -> str, for tests
        self.api_key = os.getenv("META_MODEL_API_KEY") or os.getenv("OPENAI_API_KEY")
        self.last_method = None  # "meta" or "regex", set by extract_text

    def _default_completer(self, prompt: str) -> str:
        from diligence.client import build_client, complete_json
        client = build_client()
        return complete_json(client, "Extract structured note terms as strict JSON.",
                             prompt, max_tokens=4000)

    def extract_with_meta(self, text: str) -> StructuredNote:
        prompt = f"""Extract structured note terms from this 424B2 prospectus. Return ONLY JSON matching:
        {{issuer, product_type, underlyings[], initial_levels[], notional, maturity_years, coupon_rate (decimal),
        coupon_barrier (decimal), autocall_barrier, knock_in_barrier, autocall_dates[], coupon_dates[], memory_coupon}}
        Rules: express rates and barriers as decimals of initial level (0.095 means 9.5%).
        coupon_barrier is a percentage of each underlying's initial level. memory_coupon is true
        only if the filing states unpaid coupons accrue. Omit fields the filing does not state;
        never invent values.
        Prospectus:\n{text[:200000]}"""
        completer = self.completer or self._default_completer
        raw = completer(prompt).strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1]
            if raw.rstrip().endswith("```"):
                raw = raw.rstrip()[:-3]
        data = json.loads(raw.strip())
        fields = StructuredNote.__dataclass_fields__
        return StructuredNote(**{k: v for k, v in data.items() if k in fields})

    def extract_with_regex(self, text: str) -> StructuredNote:
        t = text.lower()
        def find(pat, default):
            m = re.search(pat, t)
            return float(m.group(1))/100 if m else default/100
        note = StructuredNote()
        note.coupon_rate = find(r"coupon.*?(\d+\.?\d*)\s*%", 9.5)
        note.coupon_barrier = find(r"coupon barrier.*?(\d+\.?\d*)\s*%", 70.0)
        note.autocall_barrier = find(r"autocall.*?(\d+\.?\d*)\s*%", 100.0)
        note.knock_in_barrier = find(r"(?:knock-in|downside threshold).*?(\d+\.?\d*)\s*%", find(r"barrier.*?(\d+\.?\d*)\s*%", 60.0) * 100)
        tickers = re.findall(r"\b(SPX|NDX|RTY|AAPL|MSFT|NVDA|TSLA|AMZN)\b", text.upper())
        if tickers: note.underlyings = list(dict.fromkeys(tickers))[:3]
        note.initial_levels = [100.0]*len(note.underlyings)
        return note

    def extract_text(self, text: str) -> StructuredNote:
        if self.api_key or self.completer:
            try:
                note = self.extract_with_meta(text)
                self.last_method = "meta"
                return note
            except Exception as e:
                print(f"[Meta Fallback] {e}")
        self.last_method = "regex"
        return self.extract_with_regex(text)

    def extract(self, filepath: str) -> StructuredNote:
        text = open(filepath, encoding="utf-8", errors="ignore").read()
        return self.extract_text(text)
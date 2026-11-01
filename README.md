# Muse

## Architecture


Raw SEC Filing (1M Context - Muse Spark)
        |
 [ParserAgent] -> Extract: Barriers, Autocall Schedule, KI, Coupons, Basket
        |
 [QuantAgent]  -> Generate: Verifiable Payoff Class
        |
 [MC Agent + Modal Sandboxes] -> 50,000 Paths, Correlated GBM, Parallel Regimes
        |
 [VerifierAgent] -> Cross-check Payoff vs Prospectus Text, Bounds, Monotonicity
        |
 [Viz Agent - Muse Image Style] -> Payoff Diagram + Risk Heatmap PNGs



 ## Project Structure
 structured_note_stress_tester/
├── main.py
├── requirements.txt
├── agents.py
├── extractor.py
├── payoff.py
├── monte_carlo.py
├── stress.py
├── verify.py
├── visualize.py
├── examples/sample_termsheet.txt
└── tests/test_payoff.py

## Run It
bash

pip install -r requirements.txt
export ANTHROPIC_API_KEY=sk-ant-...   # optional - enables Muse 1M extraction
python main.py --filing examples/sample_termsheet.txt --paths 50000
Parallel Modal sandboxes:
modal deploy monte_carlo.py && python main.py --modal --paths 50000


## Future work
Extend: Swap extractor.py to use SEC EDGAR API (edgartools), add CLO waterfall in payoff.py, and deploy Streamlit dashboard with streamlit run app.py for client pitchbooks.

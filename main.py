# main.py
import argparse
from agents import MultiAgentOrchestrator
if __name__ == "__main__":
    p=argparse.ArgumentParser(); p.add_argument("--filing", default="examples/sample_termsheet.txt")
    p.add_argument("--paths", type=int, default=50000); p.add_argument("--modal", action="store_true")
    a=p.parse_args(); MultiAgentOrchestrator(a.filing).run(n_paths=a.paths, use_modal=a.modal)
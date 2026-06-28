"""
src/cognition/run_cycle.py

CLI entry point: run one learning cycle from a seed spec and emit the resulting
KnowledgeRecordV0 artifacts as JSONL. This is the OAA → AAA boundary file —
AAA harvests the emitted artifacts into its quarantined `experimental` tier.

Usage:
    python -m src.cognition.run_cycle --seed seed.json --out artifacts.jsonl
    python -m src.cognition.run_cycle --seed seed.json --out artifacts.jsonl --model claude-sonnet-4-6

Seed spec shape (produced by AAA's seeder, optionally with a `grounding` string):
    {
      "niche": {"description": "<question>", "required_capabilities": [...]},
      "agents": [{"agent_id": "...", "display_name": "...", "suggested_role": "...", ...}],
      "grounding": "<corpus evidence snippets, optional>"
    }
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.cognition.bridge import LearningCycle, make_cognition
from src.mouseion.substrate import Mouseion
from src.utils.helpers import get_logger

logger = get_logger("cognition.run_cycle")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run one OAA learning cycle → KnowledgeRecordV0 JSONL")
    parser.add_argument("--seed", required=True, help="Path to the seed spec JSON")
    parser.add_argument("--out", required=True, help="Path to write KnowledgeRecordV0 JSONL")
    parser.add_argument("--model", default="claude-haiku-4-5-20251001", help="LLM model id")
    args = parser.parse_args()

    seed = json.loads(Path(args.seed).read_text(encoding="utf-8"))
    logger.info("Loaded seed: question=%r, %d agents",
                seed.get("niche", {}).get("description", "")[:80], len(seed.get("agents", [])))

    cycle = LearningCycle(cognition=make_cognition(model=args.model), mouseion=Mouseion())
    records = cycle.run(seed)

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec.model_dump(mode="json"), ensure_ascii=False) + "\n")

    logger.info("Wrote %d artifacts → %s", len(records), out)
    # Print a short summary for the operator.
    for rec in records:
        kind = "SYNTHESIS" if rec.author_id.startswith("synthesizer") else "finding"
        print(f"  [{kind}] {rec.record_id}  conf={rec.confidence:.3f}  {rec.content[:70]}")


if __name__ == "__main__":
    main()

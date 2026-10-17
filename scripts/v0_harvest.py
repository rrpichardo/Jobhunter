"""Run with `uv run --locked python -m scripts.v0_harvest --output ...`."""

import argparse
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

import httpx
import yaml

from jobhunter.artifacts import write_artifact
from jobhunter.fetch import JsonFetcher
from jobhunter.greenhouse import collect_board, is_pm_candidate


def main(argv=None, *, client=None) -> int:
    parser = argparse.ArgumentParser(description="M0 Greenhouse sample; no Sheet writes or social access.")
    parser.add_argument("--config", default="sources/m0_sources.yaml")
    parser.add_argument("--output", required=True, help="New artifact path outside checkout; never overwritten")
    parser.add_argument("--limit", type=int, choices=range(1, 11), default=1)
    args = parser.parse_args(argv)
    owned = client is None
    client = client or httpx.Client()
    try:
        config = yaml.safe_load(Path(args.config).read_text(encoding="utf-8"))
        if not isinstance(config, dict) or set(config) != {"board", "company", "ai_company"}:
            raise ValueError("invalid_registry")
        if (not isinstance(config["company"], str) or not config["company"].strip()
                or type(config["ai_company"]) is not bool):
            raise ValueError("invalid_registry")
        captured_at = datetime.now(timezone.utc).isoformat()
        result = collect_board(JsonFetcher(client), captured_at=captured_at, **config)
        candidates = [job for job in result.jobs if is_pm_candidate(job.title)]
        selected = candidates[:args.limit]
        write_artifact(args.output, {
            "schema_version": 1, "source": {
                "source_id": result.source_id, "status": result.status,
                "captured_at": captured_at, "jobs_fetched": len(result.jobs),
                "pm_candidates": len(candidates), "selected_for_m0": len(selected),
                "coverage": result.coverage, "selection": "bounded-m0-sample",
                "error": result.error,
            }, "jobs": [asdict(job) for job in selected],
        })
        print(f"{result.status}: fetched={len(result.jobs)} selected_for_m0={len(selected)}")
        return 2 if result.status == "failed" else 0
    except (ValueError, TypeError, OSError, yaml.YAMLError):
        print("harvest_failed: invalid_input_or_artifact")
        return 2
    finally:
        if owned:
            client.close()


if __name__ == "__main__":
    raise SystemExit(main())

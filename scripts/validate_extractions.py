"""Validate Claude's proposed source excerpts and derive records in Python."""

import argparse

from jobhunter.artifacts import read_artifact, write_artifact
from jobhunter.records import SourceJob, validate_extractions


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Validate M0 source facts; never writes a Sheet.")
    parser.add_argument("--harvest", required=True)
    parser.add_argument("--extractions", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    try:
        harvest, facts = read_artifact(args.harvest), read_artifact(args.extractions)
        if not isinstance(harvest, dict) or harvest.get("schema_version") != 1:
            raise ValueError("invalid_harvest_version")
        if not isinstance(harvest.get("jobs"), list):
            raise ValueError("invalid_harvest_jobs")
        source = harvest.get("source")
        if not isinstance(source, dict) or source.get("status") not in {"OK", "OK-zero-jobs"}:
            raise ValueError("source_not_successful")
        jobs = [SourceJob(**item) for item in harvest["jobs"]]
        rows = validate_extractions(jobs, facts)
        write_artifact(args.output, {"schema_version": 1, "source": source, "jobs": rows})
        print(f"validated_records={len(rows)}; Sheet delivery not attempted")
        return 0
    except (ValueError, TypeError, OSError):
        print("validation_failed: invalid_input_or_artifact")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

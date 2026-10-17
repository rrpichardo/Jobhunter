from dataclasses import asdict
import json
from pathlib import Path

import httpx
import pytest

from test_m0_records import source


def test_harvest_saves_bounded_sample_and_truthful_coverage(tmp_path):
    from scripts.v0_harvest import main
    config = tmp_path / "sources.yaml"
    config.write_text("board: example\ncompany: Example\nai_company: true\n")
    item = {"id": 101, "title": "AI Product Manager", "content": "Build AI products.",
            "absolute_url": "https://example.com/jobs/101"}
    client = httpx.Client(transport=httpx.MockTransport(lambda req: httpx.Response(
        200, json={"jobs": [item, item | {"id": 102}]})))
    target = tmp_path / "harvest.json"
    assert main(["--config", str(config), "--output", str(target)], client=client) == 0
    payload = json.loads(target.read_text())
    assert len(payload["jobs"]) == 1
    assert payload["source"]["jobs_fetched"] == 2
    assert payload["source"]["pm_candidates"] == 2
    assert payload["source"]["selected_for_m0"] == 1
    assert payload["source"]["coverage"] == "complete-response"


def test_validation_cli_roundtrip_and_rejects_unknown_or_duplicate_source_ids(tmp_path):
    from scripts.validate_extractions import main
    harvest, facts, output = [tmp_path / name for name in ("harvest.json", "facts.json", "rows.json")]
    harvest.write_text(json.dumps({"schema_version": 1, "source": {"status": "OK"},
                                   "jobs": [asdict(source())]}))
    facts.write_text(json.dumps([{"job_id": source().job_id, "description_quote": "Build safe AI"}]))
    assert main(["--harvest", str(harvest), "--extractions", str(facts), "--output", str(output)]) == 0
    assert json.loads(output.read_text())["jobs"][0]["Job ID"] == source().job_id
    assert main(["--harvest", str(harvest), "--extractions", str(facts), "--output", str(output)]) == 2


def test_artifacts_cannot_be_written_into_repository_or_overwrite_existing_files(tmp_path):
    from jobhunter.artifacts import write_artifact
    repo = Path(__file__).resolve().parents[1]
    with pytest.raises(ValueError, match="outside_checkout"):
        write_artifact(repo / "bad-test-artifact.json", {})
    path = tmp_path / "existing.json"
    path.write_text("keep")
    with pytest.raises(FileExistsError):
        write_artifact(path, {})
    assert path.read_text() == "keep"


def test_invalid_model_file_has_sanitized_failure_and_no_partial_output(tmp_path, capsys):
    from scripts.validate_extractions import main
    harvest, facts, output = [tmp_path / name for name in ("harvest.json", "facts.json", "rows.json")]
    harvest.write_text(json.dumps({"schema_version": 1, "jobs": [asdict(source())]}))
    facts.write_text("private input / malformed JSON")
    assert main(["--harvest", str(harvest), "--extractions", str(facts), "--output", str(output)]) == 2
    assert not output.exists()
    assert "private input" not in capsys.readouterr().out


def test_failed_source_is_recorded_with_nonzero_exit(tmp_path):
    from scripts.v0_harvest import main
    config, output = tmp_path / "config.yaml", tmp_path / "failed.json"
    config.write_text("board: example\ncompany: Example\nai_company: true\n")
    client = httpx.Client(transport=httpx.MockTransport(lambda req: httpx.Response(403)))
    assert main(["--config", str(config), "--output", str(output)], client=client) == 2
    payload = json.loads(output.read_text())
    assert payload["source"]["status"] == "failed"
    assert payload["source"]["error"] == "http_403"
    assert payload["jobs"] == []

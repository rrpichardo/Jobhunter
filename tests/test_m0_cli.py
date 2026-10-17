from dataclasses import asdict
import json
import hashlib
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
        200, json={"jobs": [item, item | {"id": 102}], "meta": {"total": 2}})))
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
    digest = hashlib.sha256(harvest.read_bytes()).hexdigest()
    assert main(["--harvest", str(harvest), "--harvest-sha256", digest,
                 "--extractions", str(facts), "--output", str(output)]) == 0
    assert json.loads(output.read_text())["jobs"][0]["Job ID"] == source().job_id
    assert main(["--harvest", str(harvest), "--harvest-sha256", digest,
                 "--extractions", str(facts), "--output", str(output)]) == 2


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
    digest = hashlib.sha256(harvest.read_bytes()).hexdigest()
    assert main(["--harvest", str(harvest), "--harvest-sha256", digest,
                 "--extractions", str(facts), "--output", str(output)]) == 2
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


def test_doomed_output_path_does_not_spend_a_live_request(tmp_path):
    from scripts.v0_harvest import main
    config, output = tmp_path / "config.yaml", tmp_path / "harvest.json"
    config.write_text("board: example\ncompany: Example\nai_company: true\n")
    output.write_text("keep")
    calls = []
    client = httpx.Client(transport=httpx.MockTransport(lambda req: calls.append(1)))
    assert main(["--config", str(config), "--output", str(output)], client=client) == 2
    assert calls == []


def test_digest_mismatch_and_nested_json_are_rejected_without_raw_errors(tmp_path):
    from jobhunter.artifacts import read_artifact
    path = tmp_path / "input.json"
    path.write_text('{"jobs": []}')
    with pytest.raises(ValueError, match="digest_mismatch"):
        read_artifact(path, expected_sha256="0" * 64)
    path.write_text("[" * 2000 + "]" * 2000)
    with pytest.raises(ValueError, match="invalid_json"):
        read_artifact(path)


def test_artifact_is_not_visible_at_final_path_until_fully_flushed(tmp_path, monkeypatch):
    import os
    from jobhunter.artifacts import write_artifact
    target = tmp_path / "published.json"
    original = os.fsync
    def during_flush(fd):
        assert not target.exists()
        original(fd)
    monkeypatch.setattr(os, "fsync", during_flush)
    write_artifact(target, {"complete": True})
    assert json.loads(target.read_text()) == {"complete": True}


def test_empty_extraction_records_partial_status_and_returns_nonzero(tmp_path):
    from scripts.validate_extractions import main
    harvest, facts, output = [tmp_path / name for name in ("harvest.json", "facts.json", "rows.json")]
    harvest.write_text(json.dumps({"schema_version": 1, "source": {"status": "OK"},
                                   "jobs": [asdict(source())]}))
    facts.write_text("[]")
    digest = hashlib.sha256(harvest.read_bytes()).hexdigest()
    assert main(["--harvest", str(harvest), "--harvest-sha256", digest,
                 "--extractions", str(facts), "--output", str(output)]) == 2
    assert json.loads(output.read_text())["extraction"] == {
        "selected": 1, "validated": 0, "status": "partial-or-empty"}

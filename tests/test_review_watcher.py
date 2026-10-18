"""Exercise the real shell watcher with GitHub responses supplied offline."""
import json
import os
from pathlib import Path
import shutil
import subprocess

import pytest

pytestmark = pytest.mark.skipif(
    os.name == "nt" or not shutil.which("bash") or not shutil.which("jq"),
    reason="The development watcher requires POSIX bash and jq",
)
HEAD = "a" * 40
BOT = "chatgpt-codex-connector"


def comment(author, body, time="2026-01-01T00:00:00Z"):
    return {"author": {"login": author}, "body": body, "createdAt": time}


def run_watcher(tmp_path, comments, heads=None, reviews=None):
    fixture = tmp_path / "response.json"
    fixture.write_text(json.dumps({"headRefOid": HEAD, "comments": comments,
                                   "reviews": reviews or []}))
    gh = tmp_path / "gh"
    gh.write_text("""#!/usr/bin/env python3
import json, os, subprocess, sys
from pathlib import Path
data = json.loads(Path(os.environ['WATCHER_FIXTURE']).read_text())
fields = sys.argv[sys.argv.index('--json') + 1].split(',')
if 'headRefOid' in fields:
    counter = Path(os.environ['WATCHER_COUNTER'])
    n = int(counter.read_text()) if counter.exists() else 0
    heads = json.loads(os.environ['WATCHER_HEADS'])
    data['headRefOid'] = heads[min(n, len(heads)-1)]
    counter.write_text(str(n+1))
result = {key: data[key] for key in fields}
if '--jq' in sys.argv:
    subprocess.run(['jq', '-r', sys.argv[sys.argv.index('--jq')+1]],
                   input=json.dumps(result), text=True, check=True)
else:
    print(json.dumps(result))
""")
    gh.chmod(0o700)
    env = {**os.environ, "PATH": str(tmp_path) + os.pathsep + os.environ["PATH"],
           "WATCHER_FIXTURE": str(fixture), "WATCHER_COUNTER": str(tmp_path / "counter"),
           "WATCHER_HEADS": json.dumps(heads or [HEAD])}
    return subprocess.run(["bash", str(Path(__file__).resolve().parents[1] /
                           "scripts/wait_codex_review.sh"), "14", HEAD, "0"],
                          env=env, capture_output=True, text=True, timeout=10)


def receipt():
    return comment(BOT, "Didn't find any major issues. Reviewed commit: " + HEAD[:10])


def test_rejects_clean_review_when_pr_has_advanced(tmp_path):
    result = run_watcher(tmp_path, [receipt()], heads=["b" * 40])
    assert result.returncode == 3, result.stdout + result.stderr
    assert "CODEX_CLEAN" not in result.stdout


def test_rechecks_head_before_clean_exit(tmp_path):
    result = run_watcher(tmp_path, [receipt()], heads=[HEAD, "b" * 40])
    assert result.returncode == 3, result.stdout + result.stderr


def test_old_usage_limit_does_not_end_new_request(tmp_path):
    result = run_watcher(tmp_path, [comment(BOT, "usage limit reached"),
        comment("owner", "@codex review", "2026-01-02T00:00:00Z")])
    assert result.returncode == 3, result.stdout + result.stderr
    assert "CODEX_TIMEOUT" in result.stdout


def test_old_usage_limit_does_not_end_automatic_review_wait(tmp_path):
    # An automatic review on a new head need not add a human request comment.
    result = run_watcher(tmp_path, [comment("owner", "@codex review"),
        comment(BOT, "usage limit reached", "2026-01-02T00:00:00Z")])
    assert result.returncode == 3, result.stdout + result.stderr
    assert "CODEX_TIMEOUT" in result.stdout


def test_old_usage_limit_without_request_is_ignored(tmp_path):
    result = run_watcher(tmp_path, [comment(BOT, "usage limit reached")])
    assert result.returncode == 3, result.stdout + result.stderr
    assert "CODEX_TIMEOUT" in result.stdout


def test_current_usage_limit_is_reported(tmp_path):
    result = run_watcher(tmp_path, [comment("owner", "@codex review"),
        comment(BOT, "usage limit reached", "2999-01-02T00:00:00Z")])
    assert result.returncode == 2, result.stdout + result.stderr


def test_current_clean_receipt_is_accepted(tmp_path):
    result = run_watcher(tmp_path, [receipt()])
    assert result.returncode == 0, result.stdout + result.stderr

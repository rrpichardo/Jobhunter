import contextlib
import importlib.util
import io
import itertools
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "coverage_audit.py"
spec = importlib.util.spec_from_file_location("audit", SCRIPT)
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


def base():
    return {"run_id": "example", "searches": [
        {"id": "p", "strategy": "primary", "query": "product manager MBA", "provider": "employer"},
        {"id": "s", "strategy": "secondary", "query": "leadership graduate", "provider": "university"},
        {"id": "f", "strategy": "function", "query": "offering management", "provider": "employer"},
    ], "observations": []}


def job(search_id="p", req="123", title="Product Manager (PM)", status="verified_open", fit="high", applied="not_applied_verified", url=None):
    return {"search_id": search_id, "company": "ExampleCo", "title": title, "location": "Austin, TX",
            "requisition_id": req, "official_url": url or f"https://jobs.example.com/job/{req}",
            "source_url": "https://university.example.edu/board/123", "fit": fit,
            "eligibility": "confirmed_eligible", "official_application_status": status,
            "application_history": applied}


class CoverageTest(unittest.TestCase):
    def test_dedup_and_multi_strategy_overlap(self):
        d=base();d["observations"]=[job("p"), job("s", url="https://jobs.example.com/job/123?utm_source=mail")]
        r=audit.audit(d)
        self.assertEqual(r["summary"]["unique_jobs"], 1)
        self.assertEqual(r["summary"]["actionable_strong_missed_by_primary"], 0)
        self.assertEqual(r["jobs"][0]["search_methods"], ["primary", "secondary"])

    def test_recover_secondary_only(self):
        d=base();d["observations"]=[job("p", req="1"),job("f", req="2",title="Offering Management (PM)")]
        r=audit.audit(d)
        self.assertEqual(r["summary"]["actionable_strong_missed_by_primary"], 1)
        self.assertEqual(r["summary"]["missed_share_within_discovered_actionable"], 0.5)
        self.assertEqual(r["missed_by_primary"][0]["requisition_ids"],["2"])

    def test_distinct_requisitions_never_merged(self):
        d=base();d["observations"]=[job("p", req="1"),job("s", req="2")]
        self.assertEqual(audit.audit(d)["summary"]["unique_jobs"],2)

    def test_no_verified_open_without_official_evidence(self):
        d=base();d["observations"]=[job("s",status="unverified")]
        r=audit.audit(d)
        self.assertEqual(r["summary"]["actionable_strong_missed_by_primary"],0)
        self.assertEqual(r["summary"]["alternate_only_strong_pending_verification"],1)

    def test_applied_not_recommended(self):
        d=base();d["observations"]=[job("s",applied="applied")]
        self.assertEqual(audit.audit(d)["summary"]["actionable_strong_jobs"],0)

    def test_status_conflict_blocks_promotion(self):
        d=base();d["observations"]=[job("p",status="verified_open"),job("s",status="confirmed_closed")]
        r=audit.audit(d)
        self.assertTrue(r["jobs"][0]["status_conflict"])
        self.assertEqual(r["summary"]["actionable_strong_jobs"],0)

    def test_validations_are_strict(self):
        d=base();d["observations"]=[job("nonexistent")]
        with self.assertRaisesRegex(ValueError,"unknown search_id"):
            audit.audit(d)

    def test_nontracking_query_param_preserved(self):
        a=audit.normalized_url("https://jobs.example.com/open?id=44&utm_source=email")
        b=audit.normalized_url("https://jobs.example.com/open?id=45&utm_source=email")
        self.assertNotEqual(a,b)
        self.assertNotIn("utm",a)

    def test_normalizes_questionable_seniority_and_parens_in_title_not_filter(self):
        d=base();d["observations"]=[job("f",req="1",title="Graduate Offering Management (Sr PM)")]
        self.assertEqual(audit.audit(d)["summary"]["actionable_strong_missed_by_primary"],1)


def summary_key(result):
    s = result["summary"]
    return (s["unique_jobs"], s["actionable_strong_jobs"], s["actionable_strong_missed_by_primary"],
            s["strong_open_needs_check"], s["alternate_only_strong_pending_verification"])


class ReviewFixesTest(unittest.TestCase):
    """One test per finding of the Claude review of 87578ef (each failed before the fix)."""

    # Finding 1: the same job under two link spellings was counted twice
    def test_same_greenhouse_job_under_two_link_spellings_is_one_job(self):
        for second in ("https://job-boards.greenhouse.io/acme/jobs/123?gh_src=abc",
                       "https://boards.greenhouse.io/acme/jobs/123?gh_src=abc",
                       "https://boards.greenhouse.io/acme/jobs/123/"):
            d = base()
            d["observations"] = [job("p", req="", url="https://boards.greenhouse.io/acme/jobs/123"),
                                 job("s", req="", url=second)]
            r = audit.audit(d)
            self.assertEqual(r["summary"]["unique_jobs"], 1, second)
            self.assertEqual(r["summary"]["actionable_strong_missed_by_primary"], 0, second)

    def test_http_and_www_spellings_still_merge(self):
        d = base()
        d["observations"] = [job("p", req="", url="http://www.jobs.acme.com/j/9"),
                             job("s", req="", url="https://jobs.acme.com/j/9")]
        self.assertEqual(audit.audit(d)["summary"]["unique_jobs"], 1)

    def test_different_greenhouse_jobs_stay_separate(self):
        d = base()
        d["observations"] = [job("p", req="", url="https://boards.greenhouse.io/acme/jobs/123"),
                             job("s", req="", url="https://boards.greenhouse.io/acme/jobs/124")]
        self.assertEqual(audit.audit(d)["summary"]["unique_jobs"], 2)

    # Finding 2: the answer depended on the order of the observations
    def test_order_of_observations_never_changes_the_answer(self):
        sightings = [job("p", req="R1", url=None), job("s", req="", url="https://jobs.acme.com/careers/R1"),
                     job("f", req="R1", url="https://jobs.acme.com/careers/R1")]
        sightings[0].pop("official_url")
        answers = set()
        for order in itertools.permutations(sightings):
            d = base(); d["observations"] = [dict(o) for o in order]
            r = audit.audit(d)
            answers.add(summary_key(r))
            self.assertEqual(r["summary"]["unique_jobs"], 1)
            self.assertEqual(r["summary"]["actionable_strong_missed_by_primary"], 0)
        self.assertEqual(len(answers), 1)

    def test_shared_generic_link_with_two_requisitions_is_never_merged(self):
        shared = "https://jobs.acme.com/careers/search"
        sightings = [job("p", req="1", url=shared), job("s", req="2", url=shared), job("f", req="", url=shared)]
        answers = set()
        for order in itertools.permutations(sightings):
            d = base(); d["observations"] = [dict(o) for o in order]
            r = audit.audit(d)
            answers.add(summary_key(r))
            self.assertEqual(r["summary"]["unique_jobs"], 3)
            self.assertEqual(sum(x["ambiguous_link"] for x in r["jobs"]), 1)
        self.assertEqual(len(answers), 1)

    # Finding 3: applied-but-no-receipt must not be recommended again
    def test_application_without_company_receipt_is_not_a_missed_role(self):
        d = base()
        d["observations"] = [job("p", req="1"), job("s", req="2", applied="company_receipt_unconfirmed")]
        r = audit.audit(d)
        self.assertEqual(r["summary"]["actionable_strong_missed_by_primary"], 0)
        self.assertEqual(r["summary"]["actionable_strong_jobs"], 1)
        self.assertEqual(r["summary"]["strong_open_needs_check"], 0)

    # Finding 4: unknown stays unknown
    def test_unknown_application_history_needs_a_human_check(self):
        d = base()
        d["observations"] = [job("p", req="1"), job("s", req="2", applied="unknown")]
        r = audit.audit(d)
        self.assertEqual(r["summary"]["actionable_strong_missed_by_primary"], 0)
        self.assertEqual(r["summary"]["strong_open_needs_check"], 1)
        self.assertEqual(r["summary"]["strong_open_needs_check_missed_by_primary"], 1)
        self.assertEqual([x["check_reasons"] for x in r["jobs"] if x["needs_check"]], [["application_history_unknown"]])

    def test_omitted_history_and_unconfirmed_eligibility_need_a_human_check(self):
        omitted = job("s", req="2"); del omitted["application_history"]; omitted["eligibility"] = "possible"
        d = base(); d["observations"] = [job("p", req="1"), omitted]
        r = audit.audit(d)
        self.assertEqual(r["summary"]["actionable_strong_missed_by_primary"], 0)
        reasons = [x["check_reasons"] for x in r["jobs"] if x["needs_check"]]
        self.assertEqual(reasons, [["application_history_unknown", "eligibility_not_confirmed"]])

    # Finding 5: bad input is rejected cleanly, output is never lost or overwritten
    def test_wrong_types_are_rejected_with_a_clear_error_not_a_crash(self):
        bad_search = base(); bad_search["searches"][0]["strategy"] = ["primary"]
        bad_fit = base(); bad_fit["observations"] = [job("p", fit=["high"])]
        bad_id = base(); bad_id["observations"] = [job("p")]; bad_id["observations"][0]["search_id"] = ["p"]
        for data in (bad_search, bad_fit, bad_id):
            with self.assertRaises(ValueError):
                audit.audit(data)

    def run_cli(self, argv):
        err = io.StringIO()
        with contextlib.redirect_stderr(err), contextlib.redirect_stdout(io.StringIO()):
            code = audit.main(argv)
        return code, err.getvalue()

    def good_input(self, folder):
        d = base(); d["observations"] = [job("p", req="1")]
        path = Path(folder) / "in.json"; path.write_text(json.dumps(d)); return path

    def test_missing_output_folder_fails_cleanly_before_any_work(self):
        with tempfile.TemporaryDirectory() as td:
            code, err = self.run_cli(["--input", str(self.good_input(td)), "--output", str(Path(td) / "nope" / "out.json")])
            self.assertEqual(code, 2)
            self.assertIn("Coverage audit failed", err)

    def test_existing_output_file_is_never_overwritten(self):
        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / "out.json"; target.write_text("PRECIOUS")
            for flag in ("--output", "--markdown"):
                code, err = self.run_cli(["--input", str(self.good_input(td)), flag, str(target)])
                self.assertEqual(code, 2, flag)
                self.assertIn("already exists", err)
                self.assertEqual(target.read_text(), "PRECIOUS")

    def test_output_files_are_written_when_paths_are_free(self):
        with tempfile.TemporaryDirectory() as td:
            out, md = Path(td) / "a.json", Path(td) / "a.md"
            code, _ = self.run_cli(["--input", str(self.good_input(td)), "--output", str(out), "--markdown", str(md)])
            self.assertEqual(code, 0)
            self.assertEqual(json.loads(out.read_text())["summary"]["unique_jobs"], 1)
            self.assertIn("Search-coverage audit", md.read_text())

    def test_script_runs_directly_from_any_folder(self):
        with tempfile.TemporaryDirectory() as td:
            p = subprocess.run([sys.executable, "-I", str(SCRIPT), "--input", str(self.good_input(td))],
                               capture_output=True, text=True, cwd=td)
            self.assertEqual(p.returncode, 0, p.stderr)
            self.assertEqual(json.loads(p.stdout)["summary"]["unique_jobs"], 1)

    # Smaller points
    def test_no_primary_search_means_nothing_is_called_alternate_only(self):
        d = base(); d["searches"] = [s for s in d["searches"] if s["strategy"] != "primary"]
        d["observations"] = [job("s", status="unverified")]
        self.assertEqual(audit.audit(d)["summary"]["alternate_only_strong_pending_verification"], 0)

    def test_reported_fit_is_the_best_one_not_the_alphabetical_first(self):
        d = base(); d["observations"] = [job("p", req="1", fit="low"), job("s", req="1", fit="medium")]
        self.assertEqual(audit.audit(d)["jobs"][0]["fit"], "medium")

    def test_company_with_no_letters_or_digits_is_rejected_not_pooled_with_others(self):
        # "---" and "***" both normalise to nothing; without a check two unrelated employers share one company key
        d = base()
        d["observations"] = [job("p", req="1"), dict(job("s", req="1"), company="---"), dict(job("f", req="1"), company="***")]
        with self.assertRaisesRegex(ValueError, "company"):
            audit.audit(d)


if __name__=="__main__":
    unittest.main()

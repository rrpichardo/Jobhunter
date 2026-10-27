import importlib.util
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


def job(search_id="p", req="123", title="Product Manager (PM)", status="verified_open", fit="high", applied="unknown", url=None):
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


if __name__=="__main__":
    unittest.main()

import copy
import unittest

from sheets_upsert import prepare_sheet_rows


def job(job_id, **overrides):
    return {"Job ID": job_id, "Company": "Acme", "Job title": "AI Product Manager", **overrides}


class SheetUpsertTests(unittest.TestCase):
    def test_distinct_requisitions_with_same_company_and_title_survive(self):
        rows = prepare_sheet_rows([], [job("REQ-1"), job("REQ-2")])
        self.assertEqual({row["Job ID"] for row in rows}, {"REQ-1", "REQ-2"})

    def test_refresh_preserves_user_fields_and_updates_machine_fields(self):
        existing = [job("REQ-1", Status="Applied", Notes="Referral from Sam", **{"My rating": 5, "Salary": "old"})]
        before = copy.deepcopy(existing)
        incoming = job("REQ-1", Status="New", Notes="overwrite attempt", **{"My rating": 0, "Salary": "new"})
        rows = prepare_sheet_rows(existing, [incoming])
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["Status"], "Applied")
        self.assertEqual(rows[0]["Notes"], "Referral from Sam")
        self.assertEqual(rows[0]["My rating"], 5)
        self.assertEqual(rows[0]["Salary"], "new")
        self.assertEqual(existing, before)

    def test_new_job_defaults_and_repeated_run_are_idempotent(self):
        first = prepare_sheet_rows([], [job("REQ-1")])
        self.assertEqual(first[0]["Status"], "New")
        self.assertEqual(first[0]["Notes"], "")
        self.assertEqual(first[0]["My rating"], "")
        self.assertEqual(prepare_sheet_rows(first, [job("REQ-1")]), first)


if __name__ == "__main__":
    unittest.main()

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

    def test_duplicate_existing_ids_are_rejected_before_notes_are_lost(self):
        rows = [job("REQ-1", Notes="Keep this"), job("REQ-1", Notes="")]
        before = copy.deepcopy(rows)
        with self.assertRaisesRegex(ValueError, "Duplicate existing Job ID"):
            prepare_sheet_rows(rows, [])
        self.assertEqual(rows, before)

    def test_invalid_job_ids_are_rejected_with_a_clear_error(self):
        for invalid in [{}, {"Job ID": ""}, {"Job ID": "   "}, {"Job ID": None}, {"Job ID": 123}]:
            for rows, incoming in [([invalid], []), ([], [invalid])]:
                with self.subTest(rows=rows, incoming=incoming):
                    with self.assertRaisesRegex(ValueError, "Job ID"):
                        prepare_sheet_rows(rows, incoming)

    def test_duplicate_incoming_id_updates_one_row_and_preserves_user_data(self):
        existing = [job("REQ-1", Status="Applied", Notes="Keep this", **{"My rating": 5})]
        rows = prepare_sheet_rows(existing, [job("REQ-1", Salary="first"), job("REQ-1", Salary="latest")])
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["Salary"], "latest")
        self.assertEqual(rows[0]["Notes"], "Keep this")
        self.assertEqual(rows[0]["Status"], "Applied")
        self.assertEqual(rows[0]["My rating"], 5)

    def test_new_job_defaults_and_repeated_run_are_idempotent(self):
        first = prepare_sheet_rows([], [job("REQ-1")])
        self.assertEqual(first[0]["Status"], "New")
        self.assertEqual(first[0]["Notes"], "")
        self.assertEqual(first[0]["My rating"], "")
        self.assertEqual(prepare_sheet_rows(first, [job("REQ-1")]), first)


if __name__ == "__main__":
    unittest.main()

# Dry run: which existing Sheet rows are meant for MBA graduates of 2027

Computed October 21, 2026 from a read-only copy of the Jobs tab (710 rows) and the live public job boards. **Nothing was changed in the Sheet.**
The rule is the one in `docs/PARAMETERS.md` section 5 ("MBA 2027 rule"). Rows touched by you (Notes, My rating, or a Status other than
New): **0**, so nothing you wrote is at risk.

| Result | Rows | Meaning |
| --- | ---: | --- |
| Keep | 1 | The text says it is meant for MBA graduates of 2027 |
| Maybe | 3 | Meant for the 2027 graduating class but asks for a bachelor's or master's in computer science, no MBA wording (decision A23) |
| No, read in full | 164 | The whole posting was read (job boards) and says nothing about MBA graduates of 2027 |
| Cannot tell | 542 | Only the first 300 characters were stored (The Muse 179, X 93, newsletter 44, Jooble 50, JSearch 32, Jobicy 19, and others), or the board blocked this environment (The Muse). Neither proven yes nor no |

**Keep (1):** X post, "2027 North America Business Leadership Development Program (Full-Time MBA)" (Olam, `@handle` row).

**Maybe (3):** Databricks "Associate Product Manager, New Grad (2027 Start)"; Databricks "Product Manager, New Grad (2027) - Belgrade" (not a US place);
Figma "Early Career, Associate Product Manager (2027)".

**Proposed clean-up, waits for your "go" (decision A22):** (1) make a full backup copy of the Jobs tab; (2) copy every row except Keep (and Maybe, if
you say so) into a new tab `Archive 2026-10-21 (not MBA 2027)`; (3) remove them from Jobs. The archive tab keeps everything, so this can be undone.
The 542 "cannot tell" rows are the judgment call: erasing them follows your instruction but removes rows nobody proved are wrong.

Honest reading of the numbers: the current sources contain almost no roles written for MBA graduates of 2027. That is a source problem, not a
filter problem; see decision A25 (company MBA programs such as General Motors, school and MBA job sites).

# Synthetic civic demonstration dataset

Run `python scripts/seed_demo_data.py` from `backend/` for a read-only audit.
After reviewing the printed counts, run `python scripts/seed_demo_data.py --apply`
to replace only rows whose titles start with `[SYNTHETIC DEMO ` in `civic_db_test`.
The script refuses any other database. It preserves unmarked reports, issues,
users, and files, and never resets the database. Existing explicitly marked demo
users are reused; the script does not delete user accounts.

The dataset contains 36 linked synthetic civic issues and citizen-report rows.
Statuses are PENDING 9, ASSIGNED 7, IN_PROGRESS 8, RESOLVED 8, and CLOSED 4.
It covers the seven backend categories, with six road-damage examples and five
for each other category. Status histories follow the supported lifecycle.

Images are generated locally as category-specific illustrations and served by
the existing `/uploads/{filename}` static route. They are deliberately labeled
as synthetic and are not photographs, real citizen evidence, or proof of actual
municipal work. Selected resolved/closed examples also receive a conceptual
after-view with the same disclaimer. This is suitable for UI and analytics
demonstrations, but should not be described in research results as a dataset of
real complaint photographs.

Coordinates are small offsets from approximate locality centers in Wagholi,
Viman Nagar, Kharadi, Lohegaon, and Dhanori. They are map-demo positions, not
surveyed complaint coordinates. The seed asks `WardService` for an assignment;
without a configured official ward-boundary GeoJSON, ward remains null. No ward
is guessed or synthesized.

## Existing Civic Health Index

The seed does not change the application's formula. For at least five active
issues in the selected scope, it computes:

`0.30 × resolution + 0.20 × handling + 0.25 × severity health + 0.15 × pending-age health + 0.10 × recurrence health`

- Resolution: percentage resolved or closed.
- Handling: percentage assigned, in progress, resolved, or closed.
- Severity health: 100 minus `(25 × unresolved critical + 10 × unresolved high) / total`.
- Pending-age health: 100 minus the percentage of pending issues older than seven days.
- Recurrence health: `100 - 30 × (multi-report issues / total)`, bounded to 50–100.

The calculation uses issues with `report_count > 0` (including resolved and
closed issues) and is withheld when fewer than five issues qualify. Severity
and pending-age health are each clamped to 0–100; recurrence health is clamped
to 50–100. Existing API notices
identify development/test data as synthetic and non-official. Ward scores are
only meaningful when reliable boundaries are configured and records actually
carry those ward identifiers; otherwise report locality-level results and mark
ward-level analysis unavailable.

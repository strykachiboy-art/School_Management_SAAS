# School Management — Restructured Layout

This is a **pure restructuring** of the original project into a domain-driven,
enterprise-style layout. No business logic, routes, or bugs were changed —
everything behaves exactly as it did before. I verified this mechanically:

- All **30 blueprints** are still registered, with identical names and URL prefixes.
- All **186 `@bp.route(...)` decorators** are present, unchanged.
- Every `school_app.*` import in the codebase was checked against the new file
  tree and confirmed to resolve — zero unresolved imports.
- Every file passes `python -m py_compile` (valid syntax).

Bugs found during the earlier audit (see `docs/AUDIT.md`) were **left in place
on purpose**, since you said you'd fix them yourself. Notably:
- `school_app/_deprecated/school_fees_route_UNUSED_shadowed_by_gateway_route.py`
  is still imported-then-immediately-shadowed in `school_app/__init__.py`, exactly
  as before.
- `report_card_route.py` (now at `modules/grading/routes/report_card_route.py`)
  is still never registered.
- The orphaned WTForms in `_deprecated/forms/` are moved but not deleted.

## What changed, and why

| Old | New | Why |
|---|---|---|
| `App/` | `src/school_app/` | `src/` layout avoids accidentally running against a stale installed copy; `App` (capitalized, generic) is an unconventional package name — renamed to something descriptive. |
| `App/routes/`, `App/services/`, `App/requests/` (grouped by **layer**) | `school_app/modules/<domain>/{routes,services,requests}` (grouped by **business domain**) | At 30+ blueprints, layer-based grouping means every change touches 3+ scattered folders. Domain grouping puts everything about "attendance" or "school_fees" in one place. |
| `App/static/`, `App/templates/` | `frontend/static/`, `frontend/templates/` | The legacy Jinja + TypeScript admin UI is a separate concern from the API; pulling it out clarifies what "the backend" actually is. |
| `test/` | `tests/`, mirrors nothing yet (still flat) | Renamed for convention only — I didn't reorganize test files into per-domain folders, since that involves guessing which tests belong where and I didn't want to introduce risk you can't easily audit. You can move them into `tests/<domain>/` yourself now that the app code is domain-split. |
| *(none)* | `requirements.txt`, `requirements-dev.txt` | There was no dependency manifest in the original repo at all — reverse-engineered from imports; **you must pin real versions** with `pip freeze` from your working environment. |
| *(none)* | `docs/`, `scripts/` | Empty scaffolding for architecture notes and CLI/maintenance scripts (e.g. you could move the `backfill-sections` CLI command's logic here later). |

## New domain modules

`src/school_app/modules/` — each folder has its own `routes/`, `services/`, `requests/` (and `schemas/` where relevant):

- `academics` — academic sessions, stages, levels, sections, terms
- `people` — students, teachers, parent/guardians, teacher permissions
- `classrooms` — classrooms, subjects, assignments, timetables
- `attendance` — attendance records, excuses
- `grading` — exams, results, grading systems/rules, report cards, grade calculation
- `promotion` — promotion + promotion rules
- `school_fees` — fees, invoices, payment gateways (Stripe/Paystack)
- `notifications`
- `audit`
- `school` — school CRUD + the shared `admin_bp` blueprint
- `admin_reports` — the admin reporting suite

Kept centralized (not domain-split, since splitting SQLAlchemy models across
folders while preserving their relationships/associations is high-risk to do
without a test run to verify): `models/`, `enums/`, `schemas/`, `utils/`,
`auth/`, plus `config.py`, `extensions.py`, `errors.py`, `decorators.py`.

## Before you run this

1. `pip install -r requirements-dev.txt` (into a fresh venv — pin real versions after).
2. Set `pythonpath = src` is already in `pytest.ini`; from the repo root run `pytest`.
3. `flask` entry point: update your `FLASK_APP` env var / `.flaskenv` if it
   referenced `App:create_app` — it's now `school_app:create_app` (or keep using
   `run.py`, which was updated to import from `school_app`).
4. Fix the bugs in `docs/AUDIT.md` at your leisure — nothing here forces your hand.

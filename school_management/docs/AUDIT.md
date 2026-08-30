# School Management App — Audit & Enterprise Restructure Plan

Stack: Flask API (`App/`) + SQLAlchemy + JWT + Redis + a Rust extension (`fees_rust/`, used for fee calc via PyO3) + a legacy Jinja/TypeScript admin frontend living inside `App/static` & `App/templates` + pytest test suite (`test/`).

No `requirements.txt` exists in the repo — that alone is a gap for an "enterprise" project (see Part 3).

---

## PART 1 — Confirmed Bugs (fix these regardless of restructuring)

### 1. `App/routes/admin/school_fees.py` is dead code
In `App/__init__.py`:
```python
from App.routes.admin.school_fees import school_fees_bp                          # line 60
from App.routes.admin.payment_gateways.school_fees_gateway_route import school_fees_bp  # line 61 — silently overwrites line 60
```
I diffed the two files: `payment_gateways/school_fees_gateway_route.py` (285 lines) is a **strict superset** of `admin/school_fees.py` (188 lines) — it has everything the old file has, plus `/payments/gateway/initiate` and `/payments/gateway/webhook`. So nothing is currently lost, but the old file is a landmine: any future edit to it has zero effect and nobody will know why.
**Action:** Delete `App/routes/admin/school_fees.py`. Nothing imports it besides the shadowed line in `__init__.py`; remove that import line too.

### 2. `App/routes/admin/report_card_route.py` — never registered
Defines `report_card_bp` with 4 real endpoints (`/calculate`, `/<id>/status`, `/<id>/pin`, `/public/verify`) but it is **never imported into `App/__init__.py`**. This entire feature is unreachable in the running app.
**Action:** Either register it (`app.register_blueprint(report_card_bp, url_prefix="/report-cards")` or similar — check `App/services/report_card_service.py` for the intended prefix) or, if abandoned, delete both the route file and `App/requests/report_card.py` / `App/services/report_card_service.py`.

### 3. `App/routes/admin/dashboard.py` — empty stub
Only contains unused model imports, zero `@bp.route` decorators, not registered anywhere.
**Action:** Delete, or build it out if a dashboard summary endpoint is actually wanted.

### 4. `App/forms/*.py` — orphaned WTForms
`classroom_form.py`, `student_form.py`, `subject_form.py`, `teachers_form.py` are not imported anywhere in `App/`. The project migrated to Pydantic-style validation in `App/requests/` and these were never cleaned up.
**Action:** Delete the whole `App/forms/` directory.

---

## PART 2 — Test Coverage Gaps

### Routes with ZERO test coverage (no endpoint in the file is ever hit by a test)
- `App/routes/admin/academic_stage_route.py`
- `App/routes/admin/promotion_rule_route.py`
- `App/routes/admin/section_route.py`
- `App/routes/admin/school_route.py`
- `App/routes/admin/report_card_route.py` (also dead code — fix #2 first)
- `App/routes/admin/grading_system_route.py` (grading systems AND grading rules, 8 endpoints)
- `App/routes/admin/academic_level_route.py`

### Routes with PARTIAL coverage (some endpoints untested)
- `App/routes/admin/school_fees.py` / `payment_gateways/school_fees_gateway_route.py` — refund, discount, waive, outstanding-invoices endpoints untested
- `App/routes/admin/teacher_route.py` — update/delete/get-by-classroom untested
- `App/routes/admin/subject_route.py` — get/update untested
- `App/routes/admin/classroom_route.py` — get/update/bulk-students untested
- `App/routes/admin/term.py` — get/update/reassign-session untested
- `App/routes/admin/student_route.py` — get/update/classroom-transfer untested
- `App/routes/admin/reports/reports_routes.py` — fees report untested
- `App/routes/admin/parent_guardian.py` — get/update/unlink-student untested
- `App/routes/admin/attendance.py` — get-by-id/get-by-term untested

### Services with NO test file at all
`backfill_service.py`, `enrollment_service.py`, `academic_level_service.py`, `academic_stage_service.py`, `section_service.py`, `grading_system_service.py`, `report_card_service.py`, `google_auth_services.py`, `auth/services/forgot_password.py`, `auth/services/refresh_access_token.py`

### Good news
No stub logic found — no bare `pass`, `...`, or `NotImplementedError` bodies outside the legitimate abstract `PaymentGateway` base class. Implemented code is complete; the gaps are purely coverage and the dead files above.

---

## PART 3 — Proposed Enterprise-Grade Structure

Your current layout groups by **layer** (all routes together, all services together) which is fine at this size but doesn't scale past ~30–40 endpoints — you're already there. Enterprise Flask projects typically switch to **domain-driven module grouping**: each business domain owns its own routes+services+schemas+tests, with only cross-cutting concerns (db, auth, config) shared centrally.

```
school_management/
├── src/
│   └── school_app/                  # renamed from "App" — avoid a package
│       │                             # name that shadows the framework concept
│       ├── __init__.py              # create_app() factory only
│       ├── config.py
│       ├── extensions.py
│       ├── errors.py
│       ├── decorators.py
│       │
│       ├── core/                    # NEW: cross-cutting, framework-agnostic
│       │   ├── enums/               # (moved as-is)
│       │   └── utils/               # (moved as-is: helpers, password, validators, responses)
│       │
│       ├── auth/                    # already domain-scoped — keep, just rename subfolders:
│       │   ├── routes.py            # merge the many small route files per domain
│       │   ├── services.py
│       │   ├── requests.py          # was "request/"
│       │   └── forms.py
│       │
│       ├── modules/                 # NEW: one folder per business domain
│       │   ├── academics/           # academic_session, academic_stage, academic_level, section, term
│       │   │   ├── models.py
│       │   │   ├── routes.py
│       │   │   ├── services.py
│       │   │   └── requests.py
│       │   ├── people/              # student, teacher, parent_guardian, teacher_permission
│       │   ├── classrooms/          # classroom, classroom_subject_teacher, subject, assignment, timetable
│       │   ├── attendance/          # attendance, excuse, notification_excuse_service
│       │   ├── academics_grading/   # exam, result, grading_system, grading_rule, report_card, grade_service
│       │   ├── promotion/           # promotion, promotion_rule, promotion_history
│       │   ├── school_fees/         # school_fees, gateways/ (stripe, paystack, base)
│       │   ├── notifications/
│       │   ├── audit/               # audit_log
│       │   └── school/              # school, dashboard (if rebuilt)
│       │
│       ├── models/                  # OPTIONAL: keep centralized if you prefer one
│       │                             # source of truth for SQLAlchemy models/migrations,
│       │                             # even though routes/services are now domain-split
│       ├── schemas/
│       └── admin_reports/           # keep admin_report_* services+routes together, it's
│                                     # already a cohesive reporting sub-domain
│
├── frontend/                        # NEW: pull the Jinja+TS admin UI out of the
│   ├── templates/                   # Flask package entirely — it's a separate concern
│   ├── static/css/
│   └── static/ts/
│
├── fees_rust/                       # unchanged — already isolated correctly
│
├── tests/                           # renamed from "test/", mirror module structure:
│   ├── conftest.py
│   ├── academics/
│   ├── people/
│   ├── classrooms/
│   ├── attendance/
│   ├── grading/
│   ├── promotion/
│   ├── school_fees/
│   ├── notifications/
│   ├── audit/
│   └── auth/
│
├── migrations/                      # unchanged
├── docs/                            # NEW: architecture notes, API reference
├── scripts/                         # NEW: e.g. the backfill CLI could move here
├── requirements.txt                 # NEW — pin your deps (none currently exist!)
├── requirements-dev.txt             # NEW — pytest, etc., separate from prod deps
├── pytest.ini
├── pyproject.toml / setup.cfg       # optional, for packaging src/ layout properly
├── .env.example
└── run.py
```

### Why this layout
- **`src/` layout**: prevents accidentally importing an uninstalled/stale copy of your package; standard for anything meant to be installable/deployable.
- **`modules/` (domain-driven)**: when a bug shows up in "attendance," everything relevant is in one folder instead of scattered across `routes/admin/`, `services/`, `requests/`, `models/`. This is the biggest lever for onboarding new engineers fast.
- **`frontend/` extracted**: your Jinja templates + hand-written TS aren't part of the API's concern and currently blur what "the backend" even is. Separating them also unblocks eventually replacing that admin UI with a proper SPA without touching `App/`.
- **`requirements.txt`**: currently there is *no dependency manifest at all* — anyone cloning this repo has to reverse-engineer dependencies from `import` statements. This is the single highest-priority housekeeping item, even before file-moving.
- **Renaming `App` → `school_app`**: `App` (capitalized, generic) is unconventional for a Python package name and clashes conceptually with "the Flask app." A descriptive lowercase package name is standard practice.

### Migration order (do this yourself, in this order, testing after each step)
1. Fix the 4 confirmed bugs in Part 1 first, on the current structure. Run the full test suite — it should still pass (nothing here changes behavior except removing genuinely dead code).
2. Add `requirements.txt` (freeze from your working venv) before moving anything else.
3. Move `frontend/` out — lowest risk, since Flask's `static_folder`/`template_folder` are just config paths in `create_app()`.
4. Rename `test/` → `tests/`, no code changes needed, just update `pytest.ini`'s testpaths if it references the old name.
5. Do the `modules/` domain regrouping **one domain at a time**, run tests after every single domain move. Start with the smallest/least-connected domain (e.g. `audit` or `notifications`) to validate your process before tackling the big ones (`academics`, `school_fees`).
6. Rename `App` → `school_app` and introduce `src/` layout last, since it touches every single import statement in the codebase — do it with a scripted find/replace (`sed`) across all `.py` files for `from App.` → `from school_app.` and `import App.` → `import school_app.`, then run tests immediately.

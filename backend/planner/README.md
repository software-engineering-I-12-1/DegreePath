# Planner (US-09 and US-18)

Generates a semester-by-semester plan with OR-Tools CP-SAT and checks every plan with an
independent validator before it is shown (design §5.5, §6.1, ADR-03).

## API

`POST /api/plans/generate/` (students only, no body; always uses the caller's own profile)

| Case | Response |
| :-- | :-- |
| Plan found and validated | `200 {status: "valid", program, terms: [{term, credits, courses: [{code, title, credits, counted_for}]}], profile_version, catalog_version, unenforced_requirements}` |
| No plan exists | `200 {status: "infeasible", message: "No valid plan exists for these constraints"}` |
| Major, credit limit or target term missing | `409 PROFILE_INCOMPLETE`, `details` lists the fields |
| No requirements imported for the major | `409 PROGRAM_NOT_IMPORTED` |
| Solver hit the 10-second cap | `504 PLANNER_TIMEOUT` |
| Validator rejected the solver's plan | `500 INTERNAL_ERROR` (only violation codes are logged) |
| Admin / signed out | `403` / `401` |

`terms` lists every term from the term after the current one through the target term, including
empty ones. The student's major is matched to an imported program by name (case-insensitive).

## Files

| File | Purpose | Imports Django? |
| :-- | :-- | :-- |
| `snapshot.py` | Immutable `PlanningInput`, `Term`, `PlanEntry`, `Violation` | No |
| `engine.py` | CP-SAT model and `generate()` | No |
| `validator.py` | Independent `validate(entries, snapshot)` | No (no OR-Tools either) |
| `requirements.py` | Degree-requirement constraints and checks (the US-18 extension point) | No |
| `loader.py` | Reads the snapshot from the database in one transaction | Yes |
| `service.py` | `validate_entries(profile, entries)` for saving and exporting plans | Yes |
| `views.py`, `urls.py` | The endpoint above | Yes |
| `benchmark.py` | NFR-3 benchmark: `python -m planner.benchmark` | No |

## Integration notes

- **US-18 (elective pools, credit thresholds):** `requirements.py` enforces all three imported
  rule types in the solver and checks them independently in the validator. Completed courses can
  fill elective pools, and `max_elective_pools_per_course` limits how many pools one course fills.
  `counted_for` is a string for one pool, a list for multiple pools, or null for none. Credit
  thresholds count each eligible completed or planned course once, even if it fills a pool too.
- **US-10 (save) and US-13 (export):** replace the validation stubs with
  `planner.service.validate_entries(profile, entries)`. Entries are
  `{"course_code", "term": "Fall 2027", "counted_for"}`; the result is a list of
  `{"code", "course", "message"}`, empty when the plan is valid.
- **US-12 (conflict explanations):** the infeasible response will gain `conflicts` and
  `possibly_non_minimal` (design §5.4).

## Tests

`python manage.py test planner` covers the validator, the solver (feasible, infeasible and
timeout paths), the API, the database loader and the 20-profile p95 benchmark.

# Planner (US-09, US-12, US-18)

Generates a semester-by-semester plan with OR-Tools CP-SAT and checks every plan with an
independent validator before it is shown (design §5.5, §6.1, ADR-03). When no plan exists,
the conflict explainer names the smallest set of constraints that cannot all be met
(design §5.4, §6.3).

## API

`POST /api/plans/generate/` (students only, no body; always uses the caller's own profile)

| Case | Response |
| :-- | :-- |
| Plan found and validated | `200 {status: "valid", program, terms: [{term, credits, courses: [{code, title, credits, counted_for}]}], profile_version, catalog_version, unenforced_requirements}` |
| No plan exists | `200 {status: "infeasible", message: "No valid plan exists for these constraints", conflicts: [{type, ref, text}], possibly_non_minimal}` |
| Major, credit limit or target term missing | `409 PROFILE_INCOMPLETE`, `details` lists the fields |
| No requirements imported for the major | `409 PROGRAM_NOT_IMPORTED` |
| Solver hit the 10-second cap | `504 PLANNER_TIMEOUT` |
| Validator rejected the solver's plan | `500 INTERNAL_ERROR` (only violation codes are logged) |
| Admin / signed out | `403` / `401` |

`terms` lists every term from the term after the current one through the target term, including
empty ones. The student's major is matched to an imported program by name (case-insensitive).

### Conflict sets

`type` is one of CREDIT_CAP, TARGET_TERM, PREREQ, COREQ, OFFERING, REQUIRED_COURSE, POOL,
CREDIT_THRESHOLD and MANUAL_REVIEW. `ref` is a stable id: `profile.credit_limit`,
`profile.target_term`, `prereq:<course>:<clause position>`, `coreq:<a>:<b>`, `offering:<course>`,
`manual_review:<course>`, `required:<requirement>:<course>`, `pool:<requirement>` and
`threshold:<requirement>`. Refs starting with `profile.` are fields the student can edit.

The set is minimal: the listed constraints admit no plan, and dropping any one of them leaves
a set that does. Generation and explanation share one 28-second deadline per request; if it is
reached, untested constraints stay in the list and `possibly_non_minimal` is true. A profile
with two independent problems gets one set; the next appears after the student fixes it.

## Files

| File | Purpose | Imports Django? |
| :-- | :-- | :-- |
| `snapshot.py` | Immutable `PlanningInput`, `Term`, `PlanEntry`, `Violation` | No |
| `engine.py` | CP-SAT model and `generate()` | No |
| `conflicts.py` | `ConstraintRef` and the text for each of the nine conflict types | No |
| `explainer.py` | `explain(snapshot, deadline)`: assumption core plus deletion pass | No |
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
  Each rule is added with `ctx.add(constraint, ref)`, so an unmet required course, pool or
  threshold appears in the conflict set (US-18 AC3). The per-course pool limit is a program
  setting and stays hard; a conflict it causes is named through the pools involved. A new rule
  type needs the same: a `conflicts.py` ref and `ctx.add`.
- **US-10 (save) and US-13 (export):** replace the validation stubs with
  `planner.service.validate_entries(profile, entries)`. Entries are
  `{"course_code", "term": "Fall 2027", "counted_for"}`; the result is a list of
  `{"code", "course", "message"}`, empty when the plan is valid.
- **US-15 (suggested fixes):** each conflict's `ref` names the one thing to change; applying a
  single change and generating again is how a suggestion can be checked (US-15 AC1).

## Tests

`python manage.py test planner` covers the validator, the solver (feasible, infeasible and
timeout paths), degree requirements, the conflict explainer (17 hand-built infeasible
scenarios plus 4 for unmet degree requirements, each checked for minimality with the
generator), the API, the database loader and the timing benchmarks for generation and
explanation.

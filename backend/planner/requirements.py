"""
Degree requirements inside the planner: the one place US-09 and US-18 meet.

US-09 enforces requirements of type "required". US-18 extends this file, and only this
file, with "pool" and "credit_threshold":

1. add_constraints(): add the pool and threshold constraints to the CP-SAT model and
   return the counts_for variables, so each scheduled course can name the pool it counts
   toward. snapshot.max_pools_per_course carries the US-08 double-counting setting.
2. check(): add the matching independent checks (pool minimums reached, thresholds met,
   no course counting toward more pools than allowed). Completed courses count too.
3. Add the type to ENFORCED_TYPES.

engine.py calls add_constraints() and validator.py calls check(); neither needs to change.
This module must not import OR-Tools or Django: the validator imports it.
"""

from .snapshot import Violation

ENFORCED_TYPES = frozenset({'required'})


def unenforced(snapshot) -> tuple:
    """Names of requirements the planner does not enforce yet, shown to the student."""
    return tuple(sorted(r.name for r in snapshot.requirements if r.kind not in ENFORCED_TYPES))


def add_constraints(ctx) -> dict:
    """
    Adds degree-requirement constraints to ctx.model.

    ctx is engine.ModelContext: ctx.model (CpModel), ctx.snapshot, ctx.terms,
    ctx.take[(code, term_index)] (BoolVar, only for terms the course is offered in)
    and ctx.scheduled(code), the linear expression "1 if the course is in the plan".

    Returns counts_for: {(course_code, pool_name): BoolVar}. Empty until US-18.
    """
    snapshot = ctx.snapshot
    for code in sorted(snapshot.required_codes() - snapshot.completed):
        ctx.model.add(ctx.scheduled(code) == 1)
    return {}


def check(entries, snapshot) -> list:
    """Independent requirement checks over completed plus planned courses."""
    violations = []
    have = set(snapshot.completed) | {e.course for e in entries}
    for code in sorted(snapshot.required_codes() - have):
        names = sorted(r.name for r in snapshot.requirements if r.kind == 'required' and code in r.courses)
        violations.append(Violation('REQUIRED_COURSE', code, f'{code} is required ({", ".join(names)})'))

    pools = {r.name: r for r in snapshot.requirements if r.kind == 'pool'}
    for entry in entries:
        if entry.counted_for is None:
            continue
        target = pools.get(entry.counted_for)
        if target is None or entry.course not in target.courses:
            violations.append(Violation(
                'POOL_ALLOCATION', entry.course, f'{entry.course} cannot count toward {entry.counted_for}',
            ))
    return violations

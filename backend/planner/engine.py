"""
Plan generator (US-09): an OR-Tools CP-SAT model over the snapshot (ADR-03, design §5.5 IF-1).

One Boolean take[c, t] per not-yet-completed course c and term t in the planning window
where c is offered. Hard rules: each course at most once; at most credit_limit credits per
term; every prerequisite clause met by a completed course or one taken in a strictly earlier
term; corequisites in the same term unless the partner is completed; manual-review courses
never scheduled. Degree requirements come from requirements.add_constraints().

The objective is fewest total credits, then earliest terms. The solver runs with one worker
and a fixed seed, so the same snapshot always gives the same plan. Every plan passes the
independent validator before it is returned; if it does not, PlannerBug is raised and only
the violation codes are logged (NFR-4, NFR-5).
"""

import logging
from dataclasses import dataclass

from ortools.sat.python import cp_model

from . import requirements
from .snapshot import PlanEntry, Term
from .validator import validate

logger = logging.getLogger(__name__)

SEED = 6063
INFEASIBLE_MESSAGE = 'No valid plan exists for these constraints'


@dataclass(frozen=True)
class SolverLimits:
    wall_seconds: float
    deterministic_seconds: float


# Deterministic limit first, with the NFR-3 10-second wall clock as a backstop (ADR-03).
GENERATION_LIMITS = SolverLimits(wall_seconds=10.0, deterministic_seconds=5.0)


@dataclass(frozen=True)
class ValidPlan:
    entries: tuple
    profile_version: int
    catalog_version: int


@dataclass(frozen=True)
class Infeasible:
    message: str = INFEASIBLE_MESSAGE


@dataclass(frozen=True)
class PlannerTimeout:
    pass


class PlannerBug(Exception):
    """The solver produced a plan the validator rejects. Carries violation codes only."""

    def __init__(self, codes):
        self.codes = list(codes)
        super().__init__('Planner produced an invalid plan: ' + ', '.join(self.codes))


class ModelContext:
    """What requirements.add_constraints() needs to add its constraints."""

    def __init__(self, model, snapshot, terms, take):
        self.model = model
        self.snapshot = snapshot
        self.terms = terms
        self.take = take
        self._by_course = {}
        for (code, index), var in take.items():
            self._by_course.setdefault(code, []).append((index, var))

    def scheduled(self, code):
        """1 if the course is in the plan, else 0. Always 0 for a course with no take variables."""
        return cp_model.LinearExpr.sum([v for _, v in self._by_course.get(code, [])])

    def taken_before(self, code, index):
        """1 if the course is planned in a term strictly before term `index`."""
        return cp_model.LinearExpr.sum([v for i, v in self._by_course.get(code, []) if i < index])


def _build(snapshot):
    model = cp_model.CpModel()
    terms = snapshot.terms()
    candidates = sorted(
        code for code, c in snapshot.courses.items()
        if code not in snapshot.completed and not c.manual_review
    )
    take = {}
    for code in candidates:
        offered = snapshot.courses[code].offered
        for t in terms:
            if t.season in offered:
                take[(code, t.index)] = model.new_bool_var(f'take[{code},{t}]')
    ctx = ModelContext(model, snapshot, terms, take)

    for code in candidates:
        model.add(ctx.scheduled(code) <= 1)

    for t in terms:
        load = [snapshot.courses[code].credits * take[(code, t.index)]
                for code in candidates if (code, t.index) in take]
        model.add(cp_model.LinearExpr.sum(load) <= snapshot.credit_limit)

    for code in candidates:
        for clause in snapshot.courses[code].prereqs:
            if any(d in snapshot.completed for d in clause):
                continue
            for t in terms:
                if (code, t.index) in take:
                    earlier = [ctx.taken_before(d, t.index) for d in sorted(clause)]
                    model.add(take[(code, t.index)] <= cp_model.LinearExpr.sum(earlier))

    for a, b in sorted(snapshot.corequisites):
        if a in snapshot.completed or b in snapshot.completed:
            continue
        for t in terms:
            model.add(_var(take, a, t) == _var(take, b, t))

    counts_for = requirements.add_constraints(ctx)

    # Credits dominate: one credit outweighs any spread of courses over terms.
    weight = len(take) * (len(terms) + 1) + 1
    first = terms[0].index if terms else 0
    model.minimize(cp_model.LinearExpr.sum([
        (weight * snapshot.courses[code].credits + (index - first)) * var
        for (code, index), var in sorted(take.items())
    ]))
    return model, take, counts_for


def _var(take, code, term):
    return take.get((code, term.index), 0)


def _solver(limits):
    solver = cp_model.CpSolver()
    solver.parameters.num_workers = 1
    solver.parameters.random_seed = SEED
    solver.parameters.max_time_in_seconds = limits.wall_seconds
    solver.parameters.max_deterministic_time = limits.deterministic_seconds
    return solver


def generate(snapshot, *, limits=GENERATION_LIMITS, validator=validate):
    """Returns ValidPlan, Infeasible or PlannerTimeout; raises PlannerBug if the plan fails validation."""
    model, take, counts_for = _build(snapshot)
    solver = _solver(limits)
    status = solver.solve(model)

    if status == cp_model.INFEASIBLE:
        return Infeasible()
    if status == cp_model.MODEL_INVALID:
        logger.error('Planner model invalid')
        raise PlannerBug(['MODEL_INVALID'])
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return PlannerTimeout()

    entries = []
    for (code, index), var in take.items():
        if solver.value(var):
            pools = sorted(name for (c, name), v in counts_for.items() if c == code and solver.value(v))
            entries.append(PlanEntry(code, Term.from_index(index), pools[0] if pools else None))
    entries.sort(key=lambda e: (e.term.index, e.course))

    violations = validator(entries, snapshot)
    if violations:
        codes = sorted({v.code for v in violations})
        logger.error('Planner produced an invalid plan; violation codes: %s', ', '.join(codes))
        raise PlannerBug(codes)

    return ValidPlan(tuple(entries), snapshot.profile_version, snapshot.catalog_version)

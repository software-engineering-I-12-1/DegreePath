"""
Plan generator (US-09): an OR-Tools CP-SAT model over the snapshot (ADR-03, design §5.5 IF-1).

One Boolean take[c, t] per not-yet-completed course c and term t in the planning window.
Each course at most once (hard). The rest are constraints a student could change, added
through ModelContext.add() so the conflict explainer (explainer.py) can name them: at most
credit_limit credits per term; every prerequisite clause met by a completed course or one
taken in a strictly earlier term; corequisites in the same term unless the partner is
completed; only terms the course is offered in; manual-review courses never scheduled.
Degree requirements come from requirements.add_constraints().

The objective is fewest total credits, then earliest terms. The solver runs with one worker
and a fixed seed, so the same snapshot always gives the same plan. Every plan passes the
independent validator before it is returned; if it does not, PlannerBug is raised and only
the violation codes are logged (NFR-4, NFR-5).
"""

import logging
from dataclasses import dataclass

from ortools.sat.python import cp_model

from . import conflicts, requirements
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

    def __init__(self, model, snapshot, terms, take, guard=None):
        self.model = model
        self.snapshot = snapshot
        self.terms = terms
        self.take = take
        self._guard = guard
        self._before = {}
        self._by_course = {}
        for (code, index), var in take.items():
            self._by_course.setdefault(code, []).append((index, var))

    def scheduled(self, code):
        """1 if the course is in the plan, else 0. Always 0 for a course with no take variables."""
        return cp_model.LinearExpr.sum([v for _, v in self._by_course.get(code, [])])

    def taken_before(self, code, index):
        """
        1 if the course is planned in a term strictly before term `index`. Built as a running
        total, before[t + 1] = before[t] + take[t], so the model grows linearly with the window.
        """
        if code not in self._before:
            terms = sorted(self._by_course.get(code, []), key=lambda pair: pair[0])
            running, prefix = 0, {}
            for i, var in terms:
                prefix[i] = running
                nxt = self.model.new_bool_var(f'before[{code},{i + 1}]')
                self.model.add(nxt == running + var)
                running = nxt
            self._before[code] = (prefix, running)
        prefix, total = self._before[code]
        if index in prefix:
            return prefix[index]
        return total if prefix and index > max(prefix) else 0

    def total(self, terms):
        """A linear sum that stays a solver expression even when empty."""
        return cp_model.LinearExpr.sum(list(terms))

    def add(self, constraint, ref):
        """
        Adds a constraint the student could change. ref (a conflicts.ConstraintRef) names it
        in a conflict set: the explainer switches it on with an assumption literal, while
        generation adds it unconditionally.
        """
        added = self.model.add(constraint)
        if self._guard is not None:
            added.only_enforce_if(self._guard(ref))
        return added


def _build(snapshot, terms, candidates, guard=None, model=None):
    """
    The constraints shared by generation and explanation (ADR-03: one encoding, two models).
    take[c, t] exists for every candidate and every term in `terms`; offerings and manual
    review are constraints rather than missing variables, so the explainer can name them.
    The target term is the end of `terms` (explainer.py handles it as TARGET_TERM).
    """
    model = model or cp_model.CpModel()
    take = {(code, t.index): model.new_bool_var(f'take[{code},{t}]') for code in candidates for t in terms}
    ctx = ModelContext(model, snapshot, terms, take, guard)
    courses = snapshot.courses

    for code in candidates:
        model.add(ctx.scheduled(code) <= 1)                                    # hard

    cap = conflicts.credit_cap(snapshot)
    for t in terms:
        load = [courses[code].credits * take[(code, t.index)] for code in candidates]
        ctx.add(cp_model.LinearExpr.sum(load) <= snapshot.credit_limit, cap)

    for code in candidates:
        c = courses[code]
        if c.manual_review:
            ctx.add(ctx.scheduled(code) == 0, conflicts.manual_review(c))
        off_season = [take[(code, t.index)] for t in terms if t.season not in c.offered]
        if off_season:
            ctx.add(cp_model.LinearExpr.sum(off_season) == 0, conflicts.offering(c))
        for position, clause in enumerate(c.prereqs):
            if any(d in snapshot.completed for d in clause):
                continue
            ref = conflicts.prereq(c, position)
            for t in terms:
                earlier = [ctx.taken_before(d, t.index) for d in sorted(clause)]
                ctx.add(take[(code, t.index)] <= cp_model.LinearExpr.sum(earlier), ref)

    included = set(candidates)
    for a, b in sorted(snapshot.corequisites):
        if a in snapshot.completed or b in snapshot.completed or not {a, b} & included:
            continue
        ref = conflicts.coreq(a, b)
        for t in terms:
            ctx.add(_var(take, a, t) == _var(take, b, t), ref)

    counts_for = requirements.add_constraints(ctx)
    return model, take, counts_for


def _candidates(snapshot):
    return sorted(code for code in snapshot.courses if code not in snapshot.completed)


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
    terms = snapshot.terms()
    model, take, counts_for = _build(snapshot, terms, _candidates(snapshot))
    # Credits dominate: one credit outweighs any spread of courses over terms.
    weight = len(take) * (len(terms) + 1) + 1
    first = terms[0].index if terms else 0
    model.minimize(cp_model.LinearExpr.sum([
        (weight * snapshot.courses[code].credits + (index - first)) * var
        for (code, index), var in sorted(take.items())
    ]))
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
            allocation = pools[0] if len(pools) == 1 else (tuple(pools) if pools else None)
            entries.append(PlanEntry(code, Term.from_index(index), allocation))
    entries.sort(key=lambda e: (e.term.index, e.course))

    violations = validator(entries, snapshot)
    if violations:
        codes = sorted({v.code for v in violations})
        logger.error('Planner produced an invalid plan; violation codes: %s', ', '.join(codes))
        raise PlannerBug(codes)

    return ValidPlan(tuple(entries), snapshot.profile_version, snapshot.catalog_version)

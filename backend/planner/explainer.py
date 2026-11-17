"""
Conflict explainer (US-12; design §6.3, Figure 7, ADR-03).

When generation is infeasible, explain() builds a second CP-SAT model from the same
encoding as engine.generate(), with no objective. Each explainable constraint (the nine
conflicts.TYPES) is switched on by its own assumption literal. The solver returns a subset
of assumptions that is enough for infeasibility; a deletion pass then drops one constraint
at a time and leaves it out only if the rest is still infeasible. The result is minimal:
the reported constraints admit no plan, and dropping any one of them leaves a set that does.

Only courses that can matter are modeled: those named by an enforced requirement plus
everything reachable through prerequisites and corequisites.

TARGET_TERM is handled by the window rather than a literal, which keeps every solve small.
The core and deletion pass run over the student's own window (next term through target
term). One more solve then asks whether that set still has no plan over a window long enough
for any plan (two terms per course covers waiting for the right season). If a plan appears,
the target term is part of the conflict and is added; if not, it is not involved.

Every solve shares one deadline (design DR-8: request start + 28 s). If it is reached, the
constraints not yet tested stay in the set, including the target term, and the result is
labeled possibly non-minimal (US-12 AC4). Nothing here logs course codes (NFR-5).
"""

import logging
import time
from dataclasses import dataclass

from ortools.sat.python import cp_model

from . import conflicts, requirements
from .engine import SEED, _build
from .snapshot import Term, terms_from

logger = logging.getLogger(__name__)

# Design DR-8: one deadline for the whole request, leaving 2 s under the NFR-3 30 s limit.
REQUEST_DEADLINE_SECONDS = 28.0


@dataclass(frozen=True)
class Explanation:
    conflicts: tuple            # ConstraintRef, in conflicts.TYPES order
    possibly_non_minimal: bool


def relevant_courses(snapshot):
    """
    Courses an enforced requirement can reach through prerequisites and corequisites, not
    yet completed. Every other course can simply be left out of a plan, so it never takes
    part in a conflict. Requirement types the planner does not enforce add nothing.
    """
    enforced = [r for r in snapshot.requirements if r.kind in requirements.ENFORCED_TYPES]
    pending = [c for r in enforced for c in r.courses]
    for r in enforced:
        if r.kind == 'credit_threshold':
            pending += [code for code, c in snapshot.courses.items() if c.level >= r.min_level]
    partners = {}
    for a, b in snapshot.corequisites:
        partners.setdefault(a, set()).add(b)
        partners.setdefault(b, set()).add(a)

    seen = set()
    while pending:
        code = pending.pop()
        if code in seen or code not in snapshot.courses or code in snapshot.completed:
            continue
        seen.add(code)
        pending += [d for clause in snapshot.courses[code].prereqs for d in clause]
        pending += sorted(partners.get(code, ()))
    return sorted(seen)


def explanation_terms(snapshot, candidates):
    last = max(snapshot.target_term.index, snapshot.first_term.index + 2 * len(candidates) + 1)
    return terms_from(snapshot.first_term, Term.from_index(last))


class _Model:
    """The guarded model over `terms` plus one solve per call, all against a shared deadline."""

    def __init__(self, snapshot, terms, candidates, deadline, clock):
        self.deadline = deadline
        self.clock = clock
        self.literals = {}
        self.model = cp_model.CpModel()
        _build(snapshot, terms, candidates, guard=self._literal, model=self.model)
        self.by_index = {lit.index: ref for ref, lit in self.literals.items()}

    def _literal(self, ref):
        if ref not in self.literals:
            self.literals[ref] = self.model.new_bool_var(f'use[{len(self.literals)}]')
        return self.literals[ref]

    def solve(self, active):
        """Returns ('infeasible', core), ('feasible', None) or ('unknown', None)."""
        remaining = self.deadline - self.clock()
        if remaining <= 0:
            return 'unknown', None
        self.model.clear_assumptions()
        self.model.add_assumptions([self.literals[ref] for ref in active])
        solver = cp_model.CpSolver()
        solver.parameters.num_workers = 1
        solver.parameters.random_seed = SEED
        solver.parameters.max_time_in_seconds = remaining
        status = solver.solve(self.model)
        if status == cp_model.INFEASIBLE:
            core = {self.by_index[i] for i in solver.sufficient_assumptions_for_infeasibility()}
            return 'infeasible', core
        if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            return 'feasible', None
        return 'unknown', None


def _sorted(refs):
    return tuple(sorted(refs, key=lambda r: r.sort_key()))


def explain(snapshot, deadline, *, clock=time.monotonic):
    """deadline is a clock() value, normally request start + REQUEST_DEADLINE_SECONDS."""
    candidates = relevant_courses(snapshot)
    target = conflicts.target_term(snapshot)
    window = _Model(snapshot, snapshot.terms(), candidates, deadline, clock)
    everything = _sorted(window.literals)

    outcome, core = window.solve(everything)
    if outcome == 'unknown':
        return Explanation(_sorted(everything + (target,)), possibly_non_minimal=True)
    if outcome == 'feasible':
        # Generation said infeasible but the explanation model found a plan: a modeling bug.
        logger.error('Conflict explainer found no conflict for an infeasible profile')
        return Explanation((), possibly_non_minimal=True)

    kept, pending = [], list(_sorted(core))
    while pending:
        candidate = pending.pop(0)
        outcome, core = window.solve(kept + pending)
        if outcome == 'infeasible':
            # Still infeasible without the candidate: leave it out, and shrink to the new core.
            pending = [ref for ref in pending if ref in core]
        elif outcome == 'feasible':
            kept.append(candidate)
        else:
            return Explanation(_sorted(kept + [candidate] + pending + [target]), possibly_non_minimal=True)

    # Does the target term take part? Only if the same constraints allow a plan without it.
    unbounded = _Model(snapshot, explanation_terms(snapshot, candidates), candidates, deadline, clock)
    outcome, _ = unbounded.solve(kept)
    if outcome == 'infeasible':
        return Explanation(_sorted(kept), possibly_non_minimal=False)
    return Explanation(_sorted(kept + [target]), possibly_non_minimal=outcome == 'unknown')

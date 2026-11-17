"""
Degree rules (US-18) used by the solver and its independent validator.

add_constraints() adds required courses, elective-pool minimums, the per-course pool limit
and credit thresholds to the CP-SAT model; check() verifies the same rules without the
solver. Every rule a student's plan could break is added with ctx.add(constraint, ref), so
the conflict explainer (US-12) can name it when no plan exists (US-18 AC3).

This module must not import OR-Tools or Django: the validator imports it.
"""

from collections import deque

from . import conflicts
from .snapshot import Violation

ENFORCED_TYPES = frozenset({'required', 'pool', 'credit_threshold'})


def unenforced(snapshot) -> tuple:
    return tuple(sorted(r.name for r in snapshot.requirements if r.kind not in ENFORCED_TYPES))


def add_constraints(ctx) -> dict:
    """
    Add degree rules to CP-SAT; return pool assignments for planned courses.

    ctx is engine.ModelContext: ctx.model, ctx.snapshot, ctx.scheduled(code) ("1 if the
    course is in the plan"), ctx.total(terms) (a linear sum) and ctx.add(constraint, ref).
    Returns counts_for: {(course_code, pool_name): BoolVar}.
    """
    snap = ctx.snapshot
    for rule in snap.requirements:
        if rule.kind == 'required':
            for code in sorted(set(rule.courses) - snap.completed):
                ctx.add(ctx.scheduled(code) == 1, conflicts.required_course(rule, code))

    for rule in snap.requirements:
        if rule.kind != 'credit_threshold':
            continue
        completed = sum(snap.courses[code].credits for code in snap.completed
                        if code in snap.courses and snap.courses[code].level >= rule.min_level)
        planned = ctx.total(course.credits * ctx.scheduled(code) for code, course in sorted(snap.courses.items())
                            if code not in snap.completed and course.level >= rule.min_level)
        ctx.add(planned >= rule.min_credits - completed, conflicts.credit_threshold(rule))

    counts_for = {}
    by_course = {}
    for pool in (r for r in snap.requirements if r.kind == 'pool'):
        allocations = []
        for code in sorted(set(pool.courses) & snap.courses.keys()):
            var = ctx.model.new_bool_var(f'counts_for[{code},{pool.name}]')
            if code not in snap.completed:
                ctx.model.add(var <= ctx.scheduled(code))
                counts_for[(code, pool.name)] = var
            allocations.append(var)
            by_course.setdefault(code, []).append(var)
        ctx.add(ctx.total(allocations) >= pool.choose_n, conflicts.pool(pool))
    # The per-course pool limit is a program setting, not something the student can change,
    # so it stays hard; a conflict it causes is named through the pools involved.
    for allocations in by_course.values():
        ctx.model.add(ctx.total(allocations) <= snap.max_pools_per_course)
    return counts_for


def _completed_can_fill(deficits, completed, pools, limit):
    """Max flow over completed courses and remaining elective-pool slots."""
    if not any(deficits.values()):
        return True
    source, sink = ('source',), ('sink',)
    residual = {}

    def edge(start, end, capacity):
        residual.setdefault(start, {})[end] = capacity
        residual.setdefault(end, {})[start] = 0

    for code in sorted(completed):
        eligible = [pool.name for pool in pools if code in pool.courses and deficits[pool.name]]
        if eligible:
            node = ('course', code)
            edge(source, node, min(limit, len(eligible)))
            for name in eligible:
                edge(node, ('pool', name), 1)
    for name, amount in deficits.items():
        if amount:
            edge(('pool', name), sink, amount)

    filled = 0
    while True:
        parent = {source: None}
        queue = deque([source])
        while queue and sink not in parent:
            node = queue.popleft()
            for neighbor, capacity in residual.get(node, {}).items():
                if capacity and neighbor not in parent:
                    parent[neighbor] = node
                    queue.append(neighbor)
        if sink not in parent:
            break
        flow = min(residual[parent[node]][node] for node in _path(parent, sink))
        node = sink
        while parent[node] is not None:
            previous = parent[node]
            residual[previous][node] -= flow
            residual[node][previous] += flow
            node = previous
        filled += flow
    return filled == sum(deficits.values())


def _path(parent, sink):
    node = sink
    while parent[node] is not None:
        yield node
        node = parent[node]


def _pool_names(value):
    if value is None:
        return ()
    if isinstance(value, str):
        return (value,)
    if isinstance(value, (list, tuple)) and all(isinstance(name, str) for name in value):
        return tuple(value)
    return None


def check(entries, snapshot) -> list:
    """Check degree rules without using the solver or database."""
    violations = []
    have = set(snapshot.completed) | {entry.course for entry in entries}
    for code in sorted(snapshot.required_codes() - have):
        names = sorted(r.name for r in snapshot.requirements if r.kind == 'required' and code in r.courses)
        violations.append(Violation('REQUIRED_COURSE', code, f'{code} is required ({", ".join(names)})'))

    for rule in snapshot.requirements:
        if rule.kind == 'credit_threshold':
            credits = sum(snapshot.courses[code].credits for code in have
                          if code in snapshot.courses and snapshot.courses[code].level >= rule.min_level)
            if credits < rule.min_credits:
                violations.append(Violation('CREDIT_THRESHOLD', None,
                                            f'{rule.name} needs {rule.min_credits} credits at level {rule.min_level}'))

    pools = {r.name: r for r in snapshot.requirements if r.kind == 'pool'}
    filled = {name: set() for name in pools}
    for entry in entries:
        names = _pool_names(entry.counted_for)
        if names is None or (names and (len(names) != len(set(names)) or len(names) > snapshot.max_pools_per_course)):
            violations.append(Violation('POOL_ALLOCATION', entry.course, 'Invalid elective-pool allocation'))
            continue
        for name in names:
            pool = pools.get(name)
            if pool is None or entry.course not in pool.courses:
                violations.append(Violation('POOL_ALLOCATION', entry.course,
                                            f'{entry.course} cannot count toward {name}'))
            else:
                filled[name].add(entry.course)

    deficits = {name: max(0, pool.choose_n - len(filled[name])) for name, pool in pools.items()}
    if not _completed_can_fill(deficits, snapshot.completed, tuple(pools.values()), snapshot.max_pools_per_course):
        for name, count in deficits.items():
            if count and not _completed_can_fill({name: count}, snapshot.completed, (pools[name],),
                                                 snapshot.max_pools_per_course):
                violations.append(Violation('POOL_MINIMUM', None, f'{name} needs {pools[name].choose_n} courses'))
        if not any(v.code == 'POOL_MINIMUM' for v in violations):
            violations.append(Violation('POOL_MINIMUM', None, 'Overlapping pools need more distinct courses'))
    return violations

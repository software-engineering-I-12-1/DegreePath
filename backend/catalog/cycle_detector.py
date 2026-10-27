"""
CycleDetector for catalog imports (US-07; Sprint 2 design, Section 4.5 rules 3 and 4).

Runs on the parsed catalog before anything is written, so the import can be
rejected as a whole (NFR-4). Works on plain course codes, not models:

    prerequisites: {course_code: [clause, ...]}, each clause a list of codes that
                   are OR-ed together, the clauses AND-ed (the PrereqClause CNF)
    corequisites:  iterable of (code, code) pairs, in either order
"""
from dataclasses import dataclass

import networkx as nx

PREREQUISITE_CYCLE = 'prerequisite_cycle'
COREQUISITE_CONTRADICTION = 'corequisite_contradiction'


@dataclass(frozen=True)
class CatalogCycle:
    kind: str
    path: str  # original course codes, e.g. "A → B → C → A" or "A → B → C ⇄ A"

    @property
    def message(self):
        if self.kind == COREQUISITE_CONTRADICTION:
            return f'Corequisite contradiction detected: {self.path}'
        return f'Prerequisite cycle detected: {self.path}'


def detect_cycle(prerequisites, corequisites):
    """
    Return the first CatalogCycle found, or None if the catalog can be imported.

    Only single-course clauses add an edge (A requires B). An OR group adds none,
    because another course in the group can still satisfy it (design, Section 6.2).
    """
    edges = []
    for course, clauses in prerequisites.items():
        for clause in clauses:
            if len(clause) == 1:
                edges.append((course, clause[0]))

    # Rule 3: the mandatory prerequisite graph has no cycle.
    path = _find_loop(edges, nx.Graph())
    if path:
        return CatalogCycle(PREREQUISITE_CYCLE, path)
    # Rule 4: corequisites share a term, so no prerequisite chain may run between them.
    path = _find_loop(edges, nx.Graph(list(corequisites)))
    if path:
        return CatalogCycle(COREQUISITE_CONTRADICTION, path)
    return None


def _find_loop(edges, corequisites):
    """
    Merge each corequisite group into one node, redraw the edges between groups and
    look for a cycle. A found cycle is spelled out in original course codes, walking
    through each group with ⇄, and rotated to start at its alphabetically first code so the same
    catalog always gives the same message.
    """
    group_of = {}
    for group in nx.connected_components(corequisites):
        for course in group:
            group_of[course] = min(group)

    merged = nx.DiGraph()
    for source, target in sorted(edges):
        merged.add_edge(
            group_of.get(source, source),
            group_of.get(target, target),
            course_edge=(source, target),
        )

    try:
        cycle = nx.find_cycle(merged)
    except nx.NetworkXNoCycle:
        return None

    course_edges = [merged.edges[edge]['course_edge'] for edge in cycle]
    hops = []
    for (source, target), (next_source, _) in zip(course_edges, course_edges[1:] + course_edges[:1]):
        hops.append((source, '→'))
        if target != next_source:
            walk = nx.shortest_path(corequisites, target, next_source)
            hops.extend((course, '⇄') for course in walk[:-1])
    start = hops.index(min(hops))
    hops = hops[start:] + hops[:start]
    return ' '.join(f'{course} {arrow}' for course, arrow in hops) + f' {hops[0][0]}'

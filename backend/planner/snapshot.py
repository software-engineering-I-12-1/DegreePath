"""
Immutable planning input (design §5.5: "A snapshot is an immutable PlanningInput").

Nothing in this package except loader.py and views.py imports Django, so the engine
and the validator can be tested without a database.
"""

import re
from dataclasses import dataclass, field
from functools import total_ordering
from typing import Mapping, Optional, Union

SEASONS = ('Spring', 'Fall')
_TERM_RE = re.compile(r'^\s*(spring|fall)\s+(\d{4})\s*$', re.IGNORECASE)


@total_ordering
@dataclass(frozen=True)
class Term:
    season: str
    year: int

    @property
    def index(self) -> int:
        """Same numbering as profiles.terms: year * 2, plus 1 for Fall."""
        return self.year * 2 + SEASONS.index(self.season)

    @classmethod
    def from_index(cls, index: int) -> 'Term':
        year, season = divmod(index, 2)
        return cls(SEASONS[season], year)

    @classmethod
    def parse(cls, text: str) -> Optional['Term']:
        match = _TERM_RE.match(text or '')
        if not match:
            return None
        return cls(match.group(1).capitalize(), int(match.group(2)))

    def next(self) -> 'Term':
        return Term.from_index(self.index + 1)

    def __lt__(self, other: 'Term') -> bool:
        return self.index < other.index

    def __str__(self) -> str:
        return f'{self.season} {self.year}'


def terms_from(first: Term, last: Term) -> list:
    """Every term from first to last inclusive; empty when last is before first."""
    return [Term.from_index(i) for i in range(first.index, last.index + 1)]


@dataclass(frozen=True)
class Course:
    code: str
    title: str
    credits: int
    level: int
    offered: frozenset
    # CNF: every clause must be satisfied by one of its courses (ADR-04).
    prereqs: tuple = ()
    manual_review: bool = False


@dataclass(frozen=True)
class Requirement:
    name: str
    kind: str  # 'required', 'pool' or 'credit_threshold'
    courses: tuple = ()
    choose_n: int = 0
    min_credits: int = 0
    min_level: int = 0


@dataclass(frozen=True)
class PlanningInput:
    courses: Mapping[str, Course]
    corequisites: frozenset  # canonical (a, b) pairs with a < b
    requirements: tuple
    completed: frozenset
    credit_limit: int
    first_term: Term
    target_term: Term
    program: str = ''
    max_pools_per_course: int = 1
    profile_version: int = 0
    catalog_version: int = 0

    def terms(self) -> list:
        return terms_from(self.first_term, self.target_term)

    def required_codes(self) -> frozenset:
        return frozenset(c for r in self.requirements if r.kind == 'required' for c in r.courses)


@dataclass(frozen=True)
class PlanEntry:
    course: str
    term: Term
    counted_for: Optional[Union[str, tuple[str, ...], list[str]]] = None


@dataclass(frozen=True)
class Violation:
    code: str
    course: Optional[str]
    detail: str = field(default='', compare=False)

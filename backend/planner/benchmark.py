"""
NFR-3 benchmark for US-09 AC4: single-worker solve time over 20 representative profiles.

Run from backend/:  python -m planner.benchmark
The same profiles run in CI through planner/test_performance.py.

The catalog is the pilot major plus 60 extra electives (80 courses), so the model is the
size of a real department catalog rather than only the courses the major lists. Each profile
has a random set of completed courses (always with their prerequisites), a credit limit of
12 to 20 and a 6- to 9-term window starting in Fall 2026 or Spring 2027.
"""

import random
import statistics
import time
from collections import Counter
from dataclasses import replace

from .engine import SEED, generate
from .fixtures import course, pilot_major
from .snapshot import Term, terms_from

P95_TARGET_SECONDS = 10.0


def benchmark_catalog():
    base = pilot_major()
    rng = random.Random(SEED)
    anchors = sorted(base.courses)
    extras = []
    for n in range(60):
        level = rng.choice((2, 3, 4))
        code = f'EL-UY {level}{n:03d}'
        clauses = tuple((rng.choice(anchors),) for _ in range(rng.choice((0, 1, 1, 2))))
        offered = rng.choice((('Fall', 'Spring'), ('Fall', 'Spring'), ('Fall',), ('Spring',)))
        extras.append(course(code, rng.choice((3, 4, 4)), offered=offered, prereqs=clauses))
    courses = dict(base.courses)
    courses.update({c.code: c for c in extras})
    return replace(base, courses=courses)


def _prereq_closed_sample(snapshot, rng, p=0.35):
    """Completed courses chosen in prerequisite order, so every completed course has its prerequisites."""
    done = set()
    progress = True
    while progress:
        progress = False
        for code in sorted(snapshot.courses):
            c = snapshot.courses[code]
            if code in done or c.manual_review:
                continue
            if all(any(d in done for d in clause) for clause in c.prereqs) and rng.random() < p:
                done.add(code)
                progress = True
        p *= 0.5
    return frozenset(done)


def representative_profiles(count=20, seed=SEED):
    catalog = benchmark_catalog()
    rng = random.Random(seed)
    profiles = []
    for i in range(count):
        first = rng.choice((Term('Fall', 2026), Term('Spring', 2027)))
        window = rng.randint(6, 9)
        target = terms_from(first, Term.from_index(first.index + window - 1))[-1]
        profiles.append(replace(
            catalog,
            completed=_prereq_closed_sample(catalog, rng),
            credit_limit=rng.randint(12, 20),
            first_term=first,
            target_term=target,
            profile_version=i + 1,
        ))
    return profiles


def run(profiles):
    times, outcomes = [], Counter()
    for snapshot in profiles:
        start = time.perf_counter()
        result = generate(snapshot)
        times.append(time.perf_counter() - start)
        outcomes[type(result).__name__] += 1
    ordered = sorted(times)
    return {
        'runs': len(times),
        'p50': statistics.median(ordered),
        'p95': ordered[max(0, -(-95 * len(ordered) // 100) - 1)],   # nearest-rank 95th percentile
        'max': ordered[-1],
        'outcomes': dict(outcomes),
    }


def main():
    result = run(representative_profiles())
    print(f"Profiles: {result['runs']}  outcomes: {result['outcomes']}")
    print(f"p50 {result['p50']:.3f} s   p95 {result['p95']:.3f} s   max {result['max']:.3f} s   "
          f"(NFR-3 target: p95 <= {P95_TARGET_SECONDS:.0f} s)")


if __name__ == '__main__':
    main()


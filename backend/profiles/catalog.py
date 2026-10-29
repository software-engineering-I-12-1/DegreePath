"""
STUB catalog adapter for US-02.

When US-05 (catalog) is merged, replace the bodies of get_majors(), get_courses()
and existing_codes() with real queries. Nothing else in `profiles` should change.
Codes are normalised (trimmed, single spaces, UPPERCASE) before reaching this module.
"""

_STUB_MAJORS = [
    'Computer Science (BS)',
    'Computer Science (BA)',
]

_STUB_COURSES = [
    {'code': 'CS-UY 1114', 'title': 'Introduction to Programming'},
    {'code': 'CS-UY 1134', 'title': 'Data Structures and Algorithms'},
    {'code': 'CS-UY 2124', 'title': 'Object-Oriented Programming'},
    {'code': 'CS-UY 2134', 'title': 'Advanced Data Structures'},
    {'code': 'CS-UY 2214', 'title': 'Computer Architecture and Organization'},
    {'code': 'CS-UY 2413', 'title': 'Design and Analysis of Algorithms'},
    {'code': 'CS-UY 3224', 'title': 'Operating Systems'},
    {'code': 'CS-UY 3843', 'title': 'Software Engineering'},
    {'code': 'MA-UY 1024', 'title': 'Calculus I'},
    {'code': 'MA-UY 1124', 'title': 'Calculus II'},
    {'code': 'MA-UY 2034', 'title': 'Discrete Mathematics'},
]


def get_majors():
    return list(_STUB_MAJORS)


def get_courses():
    return [dict(c) for c in _STUB_COURSES]


def existing_codes(codes):
    """Return the subset of `codes` that exist in the catalog."""
    known = {c['code'] for c in _STUB_COURSES}
    return {c for c in codes if c in known}
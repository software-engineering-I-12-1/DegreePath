"""Course options and code validation backed by the imported catalog."""

from catalog.models import Course, DegreeProgram

_STUB_MAJORS = [
    'Computer Science (BS)',
    'Computer Science (BA)',
]

def get_majors():
    imported = DegreeProgram.objects.filter(kind='major').values_list('name', flat=True)
    return list(dict.fromkeys([*_STUB_MAJORS, *imported]))


def get_courses():
    return list(Course.objects.values('code', 'title').order_by('code'))


def existing_codes(codes):
    """Return the subset of `codes` that exist in the catalog."""
    return set(Course.objects.filter(code__in=codes).values_list('code', flat=True))

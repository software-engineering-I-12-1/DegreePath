import re

from . import catalog, terms

MAX_COURSES = 200


def normalize_code(raw):
    return re.sub(r'\s+', ' ', raw.strip()).upper()


def _whole_number(value):
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    if isinstance(value, str) and re.fullmatch(r'\d+', value.strip()):
        return int(value.strip())
    return None


def validate_profile(data):
    """Return (cleaned, errors). errors maps field name -> message; nothing is saved if non-empty."""
    cleaned, errors = {}, {}

    # Major
    major = data.get('major')
    if isinstance(major, str) and major.strip() in catalog.get_majors():
        cleaned['major'] = major.strip()
    else:
        errors['major'] = 'Choose a valid major'

    # Credit limit: whole number 1..24
    limit = _whole_number(data.get('credit_limit'))
    if limit is None or not 1 <= limit <= 24:
        errors['credit_limit'] = 'Credit limit must be a whole number from 1 to 24'
    else:
        cleaned['credit_limit'] = limit

    # Target term: "Spring 2028" / "Fall 2027", not in the past
    term_raw = data.get('target_term')
    index = terms.parse_term(term_raw) if isinstance(term_raw, str) else None
    if index is None:
        errors['target_term'] = "Enter a term like 'Spring 2028' or 'Fall 2027'"
    elif index < terms.current_term_index():
        errors['target_term'] = 'Target term cannot be in the past'
    else:
        cleaned['target_term'] = terms.format_term(index)

    # Completed courses: every code must exist in the catalog
    raw = data.get('completed_courses', [])
    if not isinstance(raw, list) or not all(isinstance(c, str) for c in raw):
        errors['completed_courses'] = 'Completed courses must be a list of course codes'
    elif len(raw) > MAX_COURSES:
        errors['completed_courses'] = f'At most {MAX_COURSES} courses allowed'
    else:
        codes = []
        for c in raw:
            code = normalize_code(c)
            if code and code not in codes:
                codes.append(code)
        known = catalog.existing_codes(codes)
        unknown = [c for c in codes if c not in known]
        if unknown:
            errors['completed_courses'] = 'Not in the catalog: ' + ', '.join(unknown)
        else:
            cleaned['completed_courses'] = codes

    return cleaned, errors
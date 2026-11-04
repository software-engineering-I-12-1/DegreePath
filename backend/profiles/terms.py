import re
from datetime import date

_TERM_RE = re.compile(r'^(spring|fall)\s+(\d{4})$', re.IGNORECASE)


def today():
    return date.today()  # patched in tests


def _index(season, year):
    return year * 2 + (0 if season == 'spring' else 1)


def current_term_index():
    t = today()
    season = 'spring' if t.month <= 5 else 'fall'
    return _index(season, t.year)


def parse_term(text):
    """'Spring 2028' -> term index, or None if the format is wrong."""
    m = _TERM_RE.match(text.strip())
    if not m:
        return None
    year = int(m.group(2))
    if not 2000 <= year <= 2100:
        return None
    return _index(m.group(1).lower(), year)


def format_term(index):
    year, s = divmod(index, 2)
    return f"{'Spring' if s == 0 else 'Fall'} {year}"


def upcoming_terms(count=10):
    start = current_term_index()
    return [format_term(start + i) for i in range(count)]
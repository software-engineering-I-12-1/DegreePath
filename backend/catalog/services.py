"""
Catalog Service Layer.
Manages transactional course import, prerequisite CNF persistence, and corequisite canonicalization (US-05, US-06).
"""

import re
from typing import List, Dict, Any, Optional, Set
from django.db import transaction
from django.db.models import F
from .models import Course, CourseOffering, PrereqClause, PrereqClauseCourse, Corequisite, CatalogState, CatalogImport
from .prereq_parser import parse_prerequisite_string, UnknownCourseError, PrereqParseError


class CatalogImportError(Exception):
    """Raised when an import batch fails validation."""
    def __init__(self, errors: List[Dict[str, Any]]):
        self.errors = errors
        msgs = "; ".join(e.get('message', str(e)) for e in errors)
        super().__init__(f"Catalog import rejected: {msgs}")


@transaction.atomic
def apply_prerequisites_to_course(
    course: Course,
    prereq_text: Optional[str],
    all_courses_by_code: Dict[str, Course],
    manual_review_codes: Set[str]
) -> None:
    """
    Parses prerequisite expression and builds normalized CNF database records (US-06 AC1, AC3, AC4).
    """
    valid_codes = set(all_courses_by_code.keys())
    result = parse_prerequisite_string(
        text=prereq_text,
        target_course_code=course.code,
        valid_catalog_codes=valid_codes
    )

    course.prereq_manual_review = result.is_manual_review
    course.prereq_raw_text = result.raw_text
    course.save(update_fields=['prereq_manual_review', 'prereq_raw_text'])

    if result.is_manual_review:
        manual_review_codes.add(course.code)

    # Wipe prior clauses for re-import idempotency (US-05 AC3)
    course.prereq_clauses.all().delete()

    # Build CNF rows
    for pos, clause_codes in enumerate(result.clauses):
        clause = PrereqClause.objects.create(course=course, position=pos)
        for req_code in clause_codes:
            req_course = all_courses_by_code[req_code]
            PrereqClauseCourse.objects.create(clause=clause, required_course=req_course)


@transaction.atomic
def apply_corequisites_to_course(
    course: Course,
    coreq_codes: List[str],
    all_courses_by_code: Dict[str, Course]
) -> None:
    """
    Canonicalizes corequisite pairs (course_id < coreq_course_id) to avoid duplicates or false cycle errors (US-06 AC2).
    """
    valid_codes = set(all_courses_by_code.keys())
    for code in coreq_codes:
        clean_code = code.strip().upper()
        if not clean_code:
            continue
        if clean_code not in valid_codes:
            raise UnknownCourseError(clean_code)
        
        partner = all_courses_by_code[clean_code]
        if course.id == partner.id:
            continue  # A course cannot be its own corequisite

        # Canonical ordering: smaller ID first (US-06 AC2)
        c1, c2 = (course, partner) if course.id < partner.id else (partner, course)
        Corequisite.objects.get_or_create(course=c1, coreq_course=c2)


def import_course_catalog(
    course_data: List[Dict[str, Any]],
    admin_user=None,
    first_row_number: int = 1,
) -> Dict[str, Any]:
    """
    Imports course catalog data in one atomic transaction (NFR-4).
    If any row or prerequisite reference is invalid, rolls back completely.
    """
    errors = []
    created_count = 0
    updated_count = 0
    manual_review_codes = set()

    # Pre-validation pass: credits, required fields, seasons
    clean_rows = []
    seen_codes = set()

    if not course_data:
        errors.append({'row': first_row_number, 'column': 'file', 'message': 'The file contains no courses'})

    for idx, row in enumerate(course_data, start=first_row_number):
        if not isinstance(row, dict):
            errors.append({'row': idx, 'column': 'row', 'message': 'Each course must be an object'})
            continue

        row_errors = []
        raw_code = row.get('code')
        code = re.sub(r'\s+', ' ', raw_code.strip()).upper() if isinstance(raw_code, str) else ''
        raw_title = row.get('title')
        title = raw_title.strip() if isinstance(raw_title, str) else ''
        if not code:
            row_errors.append({'row': idx, 'column': 'code', 'message': 'Course code is required'})
        elif code in seen_codes:
            row_errors.append({'row': idx, 'column': 'code', 'value': code, 'message': f'Duplicate course code {code} in file'})
        if not title:
            row_errors.append({'row': idx, 'column': 'title', 'message': 'Course title is required'})

        raw_credits = row.get('credits')
        if isinstance(raw_credits, bool) or not (
            isinstance(raw_credits, int) or
            (isinstance(raw_credits, str) and raw_credits.strip().isdigit())
        ):
            credits = None
        else:
            credits = int(raw_credits)
        if credits is None or not 1 <= credits <= 24:
            row_errors.append({
                'row': idx, 'column': 'credits', 'value': raw_credits,
                'message': f"Credits must be a whole number from 1 to 24; got '{raw_credits}'",
            })

        raw_offerings = row.get('offerings')
        if isinstance(raw_offerings, str):
            raw_offerings = [part.strip() for part in raw_offerings.split(',')]
        if not isinstance(raw_offerings, list) or not raw_offerings:
            raw_offerings = [raw_offerings]
        valid_seasons = []
        for season in raw_offerings:
            clean = season.strip().capitalize() if isinstance(season, str) else ''
            if clean not in ('Fall', 'Spring'):
                row_errors.append({
                    'row': idx, 'column': 'offerings', 'value': season,
                    'message': f"Invalid term-offering value '{season}'; use Fall or Spring",
                })
            else:
                valid_seasons.append(clean)

        errors.extend(row_errors)
        if row_errors:
            continue
        seen_codes.add(code)
        clean_rows.append({
            'code': code, 'title': title, 'credits': credits,
            'offerings': set(valid_seasons),
            'prerequisites': row.get('prerequisites'),
            'corequisites': row.get('corequisites'),
        })

    if errors:
        # Record rejected import
        CatalogImport.objects.create(
            admin=admin_user,
            kind='courses',
            status='rejected',
            report={'errors': errors}
        )
        raise CatalogImportError(errors)

    # Database commit pass inside atomic transaction
    try:
        with transaction.atomic():
            # 1. Upsert all Course entities
            courses_by_code = {}
            for item in clean_rows:
                course, created = Course.objects.update_or_create(
                    code=item['code'],
                    defaults={
                        'title': item['title'],
                        'credits': item['credits'],
                    }
                )
                if created:
                    created_count += 1
                else:
                    updated_count += 1

                # Offerings
                course.offerings.all().delete()
                for season in item['offerings']:
                    CourseOffering.objects.create(course=course, season=season)

                courses_by_code[item['code']] = course

            # Include any pre-existing courses already in the database for cross-batch references
            for existing in Course.objects.exclude(code__in=courses_by_code.keys()):
                courses_by_code[existing.code] = existing

            # 2. Ingest prerequisites in CNF (US-06 AC1, AC3, AC4)
            for item in clean_rows:
                course = courses_by_code[item['code']]
                if item['prerequisites'] is None:
                    continue
                apply_prerequisites_to_course(
                    course=course,
                    prereq_text=item['prerequisites'],
                    all_courses_by_code=courses_by_code,
                    manual_review_codes=manual_review_codes
                )

            # 3. Ingest corequisites with canonical ordering (US-06 AC2)
            for item in clean_rows:
                course = courses_by_code[item['code']]
                coreqs = item['corequisites']
                if coreqs is None:
                    continue
                if isinstance(coreqs, str):
                    coreqs = [c.strip() for c in coreqs.split(',') if c.strip()]
                apply_corequisites_to_course(
                    course=course,
                    coreq_codes=coreqs,
                    all_courses_by_code=courses_by_code
                )

            # 4. Atomically bump CatalogState version
            state, _ = CatalogState.objects.get_or_create(id=1)
            state.catalog_version += 1
            state.save()

            report = {
                'imported': len(clean_rows),
                'created': created_count,
                'updated': updated_count,
                'manual_review': sorted(list(manual_review_codes)),
                'catalog_version': state.catalog_version
            }

            CatalogImport.objects.create(
                admin=admin_user,
                kind='courses',
                status='accepted',
                report=report
            )

            return report

    except UnknownCourseError as err:
        err_dict = [{'row': 'prerequisites', 'column': 'prerequisites', 'message': str(err)}]
        CatalogImport.objects.create(
            admin=admin_user,
            kind='courses',
            status='rejected',
            report={'errors': err_dict}
        )
        raise CatalogImportError(err_dict)
    except Exception as exc:
        err_dict = [{'row': 'general', 'column': 'database', 'message': str(exc)}]
        CatalogImport.objects.create(
            admin=admin_user,
            kind='courses',
            status='rejected',
            report={'errors': err_dict}
        )
        raise CatalogImportError(err_dict)

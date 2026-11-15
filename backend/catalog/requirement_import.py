"""
Degree requirement import (US-08; Sprint 2 design, Section 5.3 POST /api/admin/requirement-imports).
A file defines one program; an accepted import replaces that program's previous requirements
in one transaction, and a rejected import leaves them unchanged (ADR-02, NFR-4).
"""

import re
from typing import Any, Dict, List, Optional, Tuple

from django.db import transaction

from .models import CatalogImport, CatalogState, Course, DegreeProgram, Requirement, RequirementCourse
from .services import CatalogImportError

REQUIREMENT_TYPES = (Requirement.REQUIRED, Requirement.POOL, Requirement.CREDIT_THRESHOLD)
PROGRAM_KINDS = ('major', 'minor')


def _normalize_code(raw) -> str:
    return re.sub(r'\s+', ' ', raw.strip()).upper() if isinstance(raw, str) else ''


def _positive_int(raw):
    """Returns raw as an int when it is a whole number >= 1 (JSON int or digit string), else None."""
    if isinstance(raw, bool):
        return None
    if isinstance(raw, int):
        return raw if raw >= 1 else None
    if isinstance(raw, str) and raw.strip().isdigit():
        value = int(raw.strip())
        return value if value >= 1 else None
    return None


def _validate(data) -> Tuple[Optional[Dict[str, Any]], List[Dict[str, Any]]]:
    """Checks the file shape and every rule except course existence; returns (clean, errors)."""
    errors = []
    if not isinstance(data, dict):
        return None, [{'row': None, 'column': 'file', 'message': 'Expected an object with a program and its requirements'}]

    program = data.get('program')
    program = program.strip() if isinstance(program, str) else ''
    if not program:
        errors.append({'row': None, 'column': 'program', 'message': 'Program name is required'})

    kind = data.get('kind', 'major')
    kind = kind.strip().lower() if isinstance(kind, str) else kind
    if kind not in PROGRAM_KINDS:
        errors.append({'row': None, 'column': 'kind', 'value': kind, 'message': f"Program kind must be major or minor; got '{kind}'"})

    raw_requirements = data.get('requirements')
    if not isinstance(raw_requirements, list) or not raw_requirements:
        errors.append({'row': None, 'column': 'requirements', 'message': 'The file contains no requirements'})
        raw_requirements = []

    requirements = []
    seen_names = set()
    for idx, raw in enumerate(raw_requirements, start=1):
        if not isinstance(raw, dict):
            errors.append({'row': idx, 'column': 'requirement', 'message': 'Each requirement must be an object'})
            continue

        name = raw.get('name')
        name = name.strip() if isinstance(name, str) else ''
        label = f'"{name}"' if name else f'#{idx}'
        req_type = raw.get('type')
        row_errors = []

        if not name:
            row_errors.append({'row': idx, 'column': 'name', 'message': f'Requirement {label} needs a name'})
        elif name in seen_names:
            row_errors.append({'row': idx, 'column': 'name', 'value': name, 'message': f'Duplicate requirement name "{name}" in file'})

        if req_type not in REQUIREMENT_TYPES:
            row_errors.append({
                'row': idx, 'column': 'type', 'value': req_type,
                'message': f"Requirement {label} has type '{req_type}'; use required, pool or credit_threshold",
            })
            errors.extend(row_errors)
            continue

        codes = []
        if req_type in (Requirement.REQUIRED, Requirement.POOL):
            raw_courses = raw.get('courses')
            if isinstance(raw_courses, str):
                raw_courses = raw_courses.split(',')
            if not isinstance(raw_courses, list) or not raw_courses:
                row_errors.append({'row': idx, 'column': 'courses', 'message': f'Requirement {label} lists no courses'})
                raw_courses = []
            for raw_code in raw_courses:
                code = _normalize_code(raw_code)
                if not code:
                    row_errors.append({'row': idx, 'column': 'courses', 'value': raw_code, 'message': f'Requirement {label} has a blank course code'})
                elif code in codes:
                    row_errors.append({'row': idx, 'column': 'courses', 'value': code, 'message': f'Requirement {label} lists {code} twice'})
                else:
                    codes.append(code)
        elif raw.get('courses'):
            row_errors.append({
                'row': idx, 'column': 'courses',
                'message': f'Credit threshold {label} counts any course at its level, so it must not list courses',
            })

        choose_n = min_credits = min_level = None
        if req_type == Requirement.POOL:
            choose_n = _positive_int(raw.get('choose_n'))
            if choose_n is None:
                row_errors.append({
                    'row': idx, 'column': 'choose_n', 'value': raw.get('choose_n'),
                    'message': f'Pool {label} needs choose_n, a whole number of at least 1',
                })
            elif codes and choose_n > len(codes):
                row_errors.append({
                    'row': idx, 'column': 'choose_n', 'value': choose_n,
                    'message': f'Pool {label} asks to choose {choose_n} from {len(codes)} courses',
                })
        elif req_type == Requirement.CREDIT_THRESHOLD:
            min_credits = _positive_int(raw.get('min_credits'))
            if min_credits is None:
                row_errors.append({
                    'row': idx, 'column': 'min_credits', 'value': raw.get('min_credits'),
                    'message': f'Credit threshold {label} needs min_credits, a whole number of at least 1',
                })
            if raw.get('min_level') is not None:
                min_level = _positive_int(raw.get('min_level'))
                if min_level is None:
                    row_errors.append({
                        'row': idx, 'column': 'min_level', 'value': raw.get('min_level'),
                        'message': f'Credit threshold {label} has an invalid min_level; use a course level such as 3000',
                    })

        errors.extend(row_errors)
        if name:
            seen_names.add(name)
        if not row_errors:
            requirements.append({
                'row': idx, 'name': name, 'type': req_type, 'codes': codes,
                'choose_n': choose_n, 'min_credits': min_credits, 'min_level': min_level,
            })

    return {'program': program, 'kind': kind, 'requirements': requirements}, errors


def _reject(admin_user, errors):
    record = CatalogImport.objects.create(
        admin=admin_user, kind='requirements', status='rejected', report={'errors': errors}
    )
    raise CatalogImportError(errors, import_id=record.id)


def describe_requirement(requirement: Requirement, course_count: int) -> str:
    """Plain-language rule text shared by the import summary and GET /api/programs/{id} (US-08 AC1)."""
    if requirement.type == Requirement.REQUIRED:
        return f"All {course_count} courses required"
    if requirement.type == Requirement.POOL:
        return f"Choose {requirement.choose_n} of {course_count}"
    if requirement.min_level:
        return f"At least {requirement.min_credits} credits at {requirement.min_level}-level or above"
    return f"At least {requirement.min_credits} credits"


def program_summary(program: DegreeProgram) -> Dict[str, Any]:
    requirements = []
    for requirement in program.requirements.prefetch_related('requirement_courses__course').order_by('position'):
        courses = [
            {'code': rc.course.code, 'title': rc.course.title, 'credits': rc.course.credits}
            for rc in sorted(requirement.requirement_courses.all(), key=lambda rc: rc.course.code)
        ]
        requirements.append({
            'name': requirement.name,
            'type': requirement.type,
            'description': describe_requirement(requirement, len(courses)),
            'courses': courses,
            'choose_n': requirement.choose_n,
            'min_credits': requirement.min_credits,
            'min_level': requirement.min_level,
        })
    return {'id': program.id, 'name': program.name, 'kind': program.kind, 'requirements': requirements}


def import_degree_requirements(data, admin_user=None) -> Dict[str, Any]:
    """
    Validates a requirements file and replaces the named program's definition atomically.
    Raises CatalogImportError naming the oversized pool (AC2) or unknown course (AC3).
    """
    clean, errors = _validate(data)
    if errors:
        _reject(admin_user, errors)

    referenced = {code for req in clean['requirements'] for code in req['codes']}
    courses_by_code = {course.code: course for course in Course.objects.filter(code__in=referenced)}
    unknown = [
        {
            'row': req['row'], 'column': 'courses', 'value': code,
            'message': f'Requirement "{req["name"]}" references {code}, which is not in the catalog',
        }
        for req in clean['requirements'] for code in req['codes'] if code not in courses_by_code
    ]
    if unknown:
        _reject(admin_user, unknown)

    try:
        with transaction.atomic():
            program, created = DegreeProgram.objects.get_or_create(
                name=clean['program'], defaults={'kind': clean['kind']}
            )
            if not created and program.kind != clean['kind']:
                program.kind = clean['kind']
                program.save(update_fields=['kind'])
            program.requirements.all().delete()

            for position, req in enumerate(clean['requirements']):
                requirement = Requirement.objects.create(
                    program=program, name=req['name'], type=req['type'], position=position,
                    choose_n=req['choose_n'], min_credits=req['min_credits'], min_level=req['min_level'],
                )
                RequirementCourse.objects.bulk_create(
                    RequirementCourse(requirement=requirement, course=courses_by_code[code]) for code in req['codes']
                )

            state, _ = CatalogState.objects.get_or_create(id=1)
            state.catalog_version += 1
            state.save()

            summary = program_summary(program)
            record = CatalogImport.objects.create(
                admin=admin_user, kind='requirements', status='accepted',
                report={'program': program.name, 'requirements': len(clean['requirements']),
                        'catalog_version': state.catalog_version},
            )
    except Exception as exc:
        _reject(admin_user, [{'row': None, 'column': 'database', 'message': str(exc)}])

    return {
        'import_id': record.id,
        'program_id': program.id,
        'summary': summary,
        'catalog_version': state.catalog_version,
    }

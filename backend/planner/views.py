"""POST /api/plans/generate/ (US-09; design §5.3 and the §6.1 path table)."""

import logging

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from core.errors import api_error
from profiles.models import Profile

from . import requirements
from .engine import GENERATION_LIMITS, Infeasible, PlannerBug, PlannerTimeout, generate
from .loader import ProfileIncomplete, ProgramNotImported, load_snapshot

logger = logging.getLogger(__name__)

FIELD_LABELS = {'major': 'Major', 'credit_limit': 'Credit limit per term', 'target_term': 'Target graduation term'}


def _plan_body(plan, snapshot):
    by_term = {t.index: [] for t in snapshot.terms()}
    for entry in plan.entries:
        c = snapshot.courses[entry.course]
        by_term[entry.term.index].append(
            {'code': c.code, 'title': c.title, 'credits': c.credits, 'counted_for': entry.counted_for}
        )
    return {
        'status': 'valid',
        'program': snapshot.program,
        'terms': [
            {'term': str(t), 'credits': sum(c['credits'] for c in by_term[t.index]), 'courses': by_term[t.index]}
            for t in snapshot.terms()
        ],
        'profile_version': plan.profile_version,
        'catalog_version': plan.catalog_version,
        # Requirement types the planner does not enforce yet (pools and thresholds arrive with US-18).
        'unenforced_requirements': list(requirements.unenforced(snapshot)),
    }


class GeneratePlanView(APIView):
    """Always plans from the caller's own stored profile; there is no input."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        if request.user.is_staff:
            return api_error('FORBIDDEN', 'Plans are only available to student accounts', status.HTTP_403_FORBIDDEN)

        profile, _ = Profile.objects.get_or_create(user=request.user)
        try:
            snapshot = load_snapshot(profile)
        except ProfileIncomplete as exc:
            labels = ', '.join(FIELD_LABELS[f].lower() for f in exc.missing)
            return api_error(
                'PROFILE_INCOMPLETE',
                f'Complete your profile before generating a plan: {labels}',
                status.HTTP_409_CONFLICT,
                [{'field': f, 'message': f'{FIELD_LABELS[f]} is required'} for f in exc.missing],
            )
        except ProgramNotImported as exc:
            return api_error(
                'PROGRAM_NOT_IMPORTED',
                f'Degree requirements for {exc.program} have not been imported yet',
                status.HTTP_409_CONFLICT,
            )

        try:
            result = generate(snapshot, limits=GENERATION_LIMITS)
        except PlannerBug:
            # engine.py has already logged the violation codes; never return a partial plan.
            return api_error('INTERNAL_ERROR', 'Something went wrong while planning', status.HTTP_500_INTERNAL_SERVER_ERROR)

        if isinstance(result, Infeasible):
            return Response({'status': 'infeasible', 'message': result.message})
        if isinstance(result, PlannerTimeout):
            return api_error(
                'PLANNER_TIMEOUT',
                'Planning took longer than 10 seconds. Try again, or allow more credits per term or a later target term.',
                status.HTTP_504_GATEWAY_TIMEOUT,
            )
        return Response(_plan_body(result, snapshot))

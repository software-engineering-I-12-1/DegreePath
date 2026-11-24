"""POST /api/plans/generate/ (US-09, US-12; design §5.3 and the §6.1 path table)."""

import logging
import time
from dataclasses import replace

from rest_framework import status
from rest_framework import serializers
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from core.errors import api_error
from profiles.models import Profile

from . import requirements
from .engine import GENERATION_LIMITS, Infeasible, PlannerBug, PlannerTimeout, generate
from .explainer import REQUEST_DEADLINE_SECONDS, explain
from .loader import ProfileIncomplete, ProgramNotImported, load_snapshot
from .snapshot import Term

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
        # Keep the field for any future requirement type the planner cannot enforce.
        'unenforced_requirements': list(requirements.unenforced(snapshot)),
    }


class GeneratePlanView(APIView):
    """Always plans from the caller's own stored profile; there is no input."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        started = time.monotonic()
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
            # One deadline for the whole request: explanation gets what generation did not use (DR-8).
            explanation = explain(snapshot, deadline=started + REQUEST_DEADLINE_SECONDS)
            return Response({
                'status': 'infeasible',
                'message': result.message,
                'conflicts': [c.as_dict() for c in explanation.conflicts],
                'possibly_non_minimal': explanation.possibly_non_minimal,
            })
        if isinstance(result, PlannerTimeout):
            return api_error(
                'PLANNER_TIMEOUT',
                'Planning took longer than 10 seconds. Try again, or allow more credits per term or a later target term.',
                status.HTTP_504_GATEWAY_TIMEOUT,
            )
        return Response(_plan_body(result, snapshot))


class ScenarioInput(serializers.Serializer):
    credit_limit = serializers.IntegerField(min_value=1, max_value=24)
    target_term = serializers.CharField(max_length=20)

    def validate_target_term(self, value):
        term = Term.parse(value)
        if term is None or not 2000 <= term.year <= 2100:
            raise serializers.ValidationError('Enter a term such as Spring 2029.')
        return term


class ComparePlansView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if request.user.is_staff or request.user.is_superuser:
            return api_error('FORBIDDEN', 'Plans are only available to students.', 403)
        inputs = ScenarioInput(data=request.data, many=True, min_length=2, max_length=2)
        inputs.is_valid(raise_exception=True)
        profile = Profile.objects.filter(user=request.user).first()
        if profile is None:
            return api_error('PROFILE_INCOMPLETE', 'Complete your profile first.', 409)
        try:
            snapshot = load_snapshot(profile)
        except ProfileIncomplete as exc:
            return api_error('PROFILE_INCOMPLETE', str(exc), 409)
        except ProgramNotImported as exc:
            return api_error('PROGRAM_NOT_IMPORTED', str(exc), 409)

        scenarios = [replace(snapshot, **settings) for settings in inputs.validated_data]
        if any(scenario.target_term < scenario.first_term for scenario in scenarios):
            return api_error('INVALID_TERM', 'Choose a target on or after the next planning term.', 400)
        results = []
        for scenario in scenarios:
            try:
                result = generate(scenario, limits=GENERATION_LIMITS)
            except PlannerBug:
                return api_error('INTERNAL_ERROR', 'Something went wrong while planning.', 500)
            if isinstance(result, Infeasible):
                results.append({'status': 'infeasible', 'message': result.message})
            elif isinstance(result, PlannerTimeout):
                results.append({'status': 'timeout', 'message': 'The solver reached its time limit.'})
            else:
                results.append(_plan_body(result, scenario))
        return Response(results)

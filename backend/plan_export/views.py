from django.http import HttpResponse
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from core.errors import api_error
from profiles.models import Profile

from . import adapters, service


def _load_owned(request, plan_id):
    """(plan, None) for the caller's own plan, else (None, error response): 404 unknown, 403 NOT_OWNER."""
    plan = adapters.get_plan(plan_id)
    if plan is None:
        return None, api_error('NOT_FOUND', 'Plan not found', status.HTTP_404_NOT_FOUND)
    if plan['owner_id'] != request.user.pk:
        return None, api_error('NOT_OWNER', 'You do not have access to this plan', status.HTTP_403_FORBIDDEN)
    return plan, None


class ExportStatusView(APIView):
    """GET /api/plan-export/status/[?plan_id=...]: drives the Export button (newest saved plan if no plan_id)."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        plan_id = request.query_params.get('plan_id')
        if plan_id:
            plan, error = _load_owned(request, plan_id)
            if error:
                return error
        else:
            plan = adapters.get_current_plan(request.user)

        profile = Profile.objects.filter(user=request.user).first()
        result = service.check_exportable(plan, profile)
        rows = plan['rows'] if plan else []
        return Response({
            'has_plan': plan is not None,
            'plan_id': plan['id'] if plan else None,
            'name': plan['name'] if plan else None,
            'exportable': result.ok,
            'reason': result.reason,
            'course_count': len(rows),
            'term_count': len({r['term'] for r in rows}),
        })


class ExportCsvView(APIView):
    """GET /api/plan-export/<plan_id>/csv/: downloads a saved plan as CSV, only if it passes validation."""

    permission_classes = [IsAuthenticated]

    def get(self, request, plan_id):
        plan, error = _load_owned(request, plan_id)
        if error:
            return error

        profile = Profile.objects.filter(user=request.user).first()
        result = service.check_exportable(plan, profile)
        if not result.ok:
            return api_error(
                'PLAN_NOT_EXPORTABLE',
                result.reason,
                status.HTTP_409_CONFLICT,
                [{'message': p} for p in result.problems],
            )

        content = service.build_csv(service.ordered_rows(plan['rows']))
        response = HttpResponse(content, content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = 'attachment; filename="degreepath-plan.csv"'
        return response
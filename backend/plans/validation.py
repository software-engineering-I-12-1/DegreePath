"""Integration point for the independent validator delivered with US-09/US-18."""


class PlanValidationUnavailable(Exception):
    pass


def validate_plan(entries, profile):
    """Return violations against current catalog and degree rules before saving.

    Replace this implementation with the shared independent validator once
    US-09 and US-18 land. Validation must include all degree and scheduling
    constraints and must never trust a client-supplied valid flag.
    """
    raise PlanValidationUnavailable('Plan validation is awaiting the planner integration.')

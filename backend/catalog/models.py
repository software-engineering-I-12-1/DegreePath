"""
Database models for Course Catalog and CNF Prerequisite Structures.
Implements ADR-04 (Conjunctive Normal Form Tables for Course Prerequisites).
"""

import re
from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError


def derive_course_level(course_code: str) -> int:
    """
    Derives course level (e.g. 1000, 2000, 3000, 4000) from course code numbers.
    e.g., 'CS-UY 1114' -> 1000, 'CS 2124' -> 2000, 'CS 3843' -> 3000.
    """
    match = re.search(r'(\d)(\d{3})', course_code)
    if match:
        return int(match.group(1)) * 1000
    # Fallback to 1000 if no 4-digit number found
    match_any = re.search(r'\d+', course_code)
    if match_any:
        num = int(match_any.group(0))
        return (num // 1000) * 1000 if num >= 1000 else 1000
    return 1000


class Course(models.Model):
    """
    Represents an individual course in the catalog.
    """
    code = models.CharField(max_length=30, unique=True, db_index=True)
    title = models.CharField(max_length=255)
    credits = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(24)]
    )
    level = models.PositiveSmallIntegerField(default=1000)
    prereq_manual_review = models.BooleanField(
        default=False,
        help_text="Flagged True if prerequisite contains prose requiring manual review (US-06 AC3)"
    )
    prereq_raw_text = models.TextField(
        blank=True,
        null=True,
        help_text="Original prerequisite text or prose description"
    )

    class Meta:
        ordering = ['code']
        constraints = [
            models.CheckConstraint(
                check=models.Q(credits__gt=0) & models.Q(credits__lte=24),
                name='course_credits_valid_range'
            )
        ]

    def save(self, *args, **kwargs):
        # Normalize course code formatting
        self.code = self.code.strip().upper()
        if not self.level or self.level == 1000:
            self.level = derive_course_level(self.code)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.code}: {self.title} ({self.credits} cr)"


class CourseOffering(models.Model):
    """
    Terms during which the course is offered (Fall, Spring).
    """
    SEASON_CHOICES = [
        ('Fall', 'Fall'),
        ('Spring', 'Spring'),
    ]

    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='offerings')
    season = models.CharField(max_length=10, choices=SEASON_CHOICES)

    class Meta:
        unique_together = ('course', 'season')
        ordering = ['course', 'season']

    def __str__(self):
        return f"{self.course.code} offered in {self.season}"


class PrereqClause(models.Model):
    """
    Represents one AND-ed prerequisite group for a Course (ADR-04).
    All clauses for a course must be satisfied.
    """
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='prereq_clauses')
    position = models.PositiveSmallIntegerField(default=0)

    class Meta:
        unique_together = ('course', 'position')
        ordering = ['course', 'position']

    def __str__(self):
        return f"PrereqClause #{self.position} for {self.course.code}"


class PrereqClauseCourse(models.Model):
    """
    Represents an OR-ed alternative course satisfying a PrereqClause (ADR-04).
    Satisfying any course in this clause satisfies the clause.
    """
    clause = models.ForeignKey(PrereqClause, on_delete=models.CASCADE, related_name='options')
    required_course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='required_by_clauses')

    class Meta:
        unique_together = ('clause', 'required_course')

    def clean(self):
        # A course cannot require itself
        if self.clause.course_id == self.required_course_id:
            raise ValidationError("A course cannot list itself as a prerequisite.")

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.required_course.code} in clause {self.clause_id}"


class Corequisite(models.Model):
    """
    Canonical corequisite relationship between two courses (ADR-04).
    Enforces course_id < coreq_course_id to ensure symmetric pairs are stored once.
    """
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name='corequisites_outgoing'
    )
    coreq_course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name='corequisites_incoming'
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['course', 'coreq_course'],
                name='unique_corequisite_pair'
            ),
            models.CheckConstraint(
                check=models.Q(course_id__lt=models.F('coreq_course_id')),
                name='corequisite_canonical_ordering'
            )
        ]

    def clean(self):
        if self.course_id and self.coreq_course_id and self.course_id >= self.coreq_course_id:
            raise ValidationError("Canonical ordering required: course_id must be strictly less than coreq_course_id.")

    def __str__(self):
        return f"{self.course.code} ⇄ {self.coreq_course.code}"


class CatalogState(models.Model):
    """
    Monotonically increasing catalog version tracker for plan staleness detection.
    """
    catalog_version = models.PositiveIntegerField(default=1)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Catalog Version: {self.catalog_version}"


class CatalogImport(models.Model):
    """
    Audit record for course and requirement file imports (all-or-nothing).
    """
    STATUS_CHOICES = [
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
    ]

    admin = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    kind = models.CharField(max_length=20, default='courses')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    report = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Import #{self.id} ({self.kind}) - {self.status}"

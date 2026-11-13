# CS major planning fixture

Load into an isolated development or test database with `python manage.py loaddata cs_major_catalog`.

This synthetic 25-course catalog uses CS-UY and MA-UY style codes for repeatable tests. Course titles, credits, offerings, and dependencies are demonstration data. It includes Fall-only, Spring-only, and both-season offerings, AND/OR prerequisite clauses, and a capstone/laboratory corequisite pair. Algorithms requires (Data Structures OR Object Oriented Programming II) AND Discrete Mathematics.

The fixture reserves primary keys 910001–950001 across its models and can be loaded repeatedly into the same test database. Use a fresh database when existing catalog records share these course codes.

Required courses and elective pools belong to the degree requirement format being implemented in US-08. Add companion degree rules and planner feasibility scenarios when US-08, US-09, and US-18 are integrated. This catalog supports that follow-up with upper-level electives, credit thresholds, and prerequisite alternatives.

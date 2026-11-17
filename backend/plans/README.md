# Saved plan integration (US-10)

`GET /api/plans/` lists the current student's plans as `{results: [...]}`. `GET /api/plans/{uuid}/` reopens one plan and returns 403 for another student's plan. Authentication uses the existing session and CSRF handling.

`POST /api/plans/` accepts a name and entries, for example `{"name":"Graduation plan","entries":[{"term":"Spring 2028","course_code":"CS-UY 1114"}]}`. It revalidates before persistence and snapshots course titles, credits, and current profile/catalog versions. Client-supplied validation flags and display values are ignored.

Saving calls `planner.service.validate_entries(profile, entries)` against the current profile, catalog, and degree rules. Invalid schedules return 400 INVALID_PLAN with violation details. A missing degree program returns 409 PROGRAM_NOT_IMPORTED. Pool assignments use `counted_for`, which accepts a string, a list of pool names, or null and is preserved in the saved snapshot. An empty schedule can be saved when the student's completed courses already satisfy every degree rule.

The generation page renders `frontend/src/components/SavePlanForm.tsx` for a valid result. Students name and save that schedule, follow the Open plan link, and return to it from My Plans after signing in again. Integration tests run the real generator and validator, preserve multi-pool allocations, reject tampered schedules and changed profile/rules, and verify persistence across sessions.

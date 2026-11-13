# Saved plan integration (US-10)

`GET /api/plans/` lists the current student's plans as `{results: [...]}`. `GET /api/plans/{uuid}/` reopens one plan and returns 403 for another student's plan. Authentication uses the existing session and CSRF handling.

`POST /api/plans/` accepts a name and entries, for example `{"name":"Graduation plan","entries":[{"term":"Spring 2028","course_code":"CS-UY 1114"}]}`. It revalidates before persistence and snapshots course titles, credits, and current profile/catalog versions. Client-supplied validation flags and display values are ignored.

This PR is a draft pending US-09 and US-18. Replace `plans.validation.validate_plan(entries, profile)` with the shared independent validator that reads current catalog and major requirements and returns violation details. Until that integration is available, POST returns 503 VALIDATION_UNAVAILABLE. Tests inject a validator to verify persistence and rejection behavior. Those tests do not establish scheduling or degree-rule correctness.

The US-09 generation page should render `frontend/src/components/SavePlanForm.tsx` with its generated entries. The current generation route displays an integration status message. My Plans and plan detail routes are implemented. A full generation → validation → save → reopen walkthrough remains required before marking this PR ready.

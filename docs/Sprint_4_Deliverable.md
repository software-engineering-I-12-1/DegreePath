# DegreePath — Sprint 4 Deliverable

---

## 1. Cover Page

**Project Name:** DegreePath  
**Group Number:** Software Engineering I I2 - 1  
**Course Name & Section:** Software Engineering I (CS-GY 6063 - Section 1 I2)  
**Instructor:** Prof. Raz Sarem  
**Date:** November 3, 2026  

### Team Members
- **Omkar Gadute** (`omkargadute`)
- **Achyuthan Sivasankar** (`Achyuthan-S`)
- **Maitri Savaliya** (`maitrisavaliya`)
- **Han Yang** (`DeadCardassian`)
- **Hanyue Liao** (`AlvitLiao`)

### Project Links
- **Code Repository:** [https://github.com/software-engineering-I-12-1/DegreePath](https://github.com/software-engineering-I-12-1/DegreePath)
- **Default Branch:** `dev` *(Production branch: `main`)*
- **GitHub Scrum Board:** [https://github.com/orgs/software-engineering-I-12-1/projects/2/views/1](https://github.com/orgs/software-engineering-I-12-1/projects/2/views/1)
- **Live Deployment:** [https://degreepath-web.onrender.com](https://degreepath-web.onrender.com) *(Hosted on Render with Neon PostgreSQL)*
- **Localhost Run Instructions:** Documented in [Section 4](#4-code-and-testing) and the root `README.md`.

### AI-Use Disclosure
Generative AI (Gemini 2.5 / DeepMind Antigravity CLI) was utilized by the team during Sprint 4 for scaffolding project boilerplate, writing unit and edge-case test suites, assisting with CI/CD YAML configuration, and proofreading technical documentation. All algorithmic logic (NetworkX graph cycle detection, Conjunctive Normal Form Boolean parser), database constraint designs, security gates, and code reviews were reviewed, verified, and approved by team members.

---

## 2. Sprint Backlog (Chosen Stories for Sprint 4)

### One-Sentence Sprint Goal
> *At the end of this sprint, a student can securely register, sign in, and search course offerings with prerequisites, while a catalog administrator can upload course catalogs in CSV/JSON with complex AND/OR prerequisites and have cycles automatically rejected.*

### Chosen Stories Summary (5 Members · 5 Stories · 18 Story Points · 100% Completed)

| Story ID | Requirement | Owner | Reviewer | Estimate | Status | Pull Request |
| :--- | :--- | :--- | :--- | :---: | :---: | :--- |
| **US-01** | Student Registration and Sign-in (Argon2 / Sessions) | Maitri | Han | 3 pts (M) | **Done** | [PR #7](https://github.com/software-engineering-I-12-1/DegreePath/pull/7) |
| **US-05** | Admin CSV/JSON Course Import (Transactional) | Han | Omkar | 3 pts (M) | **Done** | [PR #11](https://github.com/software-engineering-I-12-1/DegreePath/pull/11) |
| **US-04** | Course Catalog Search & Details Display | Hanyue | Achyuthan | 2 pts (S) | **Done** | [PR #12](https://github.com/software-engineering-I-12-1/DegreePath/pull/12) |
| **US-06** | AND/OR CNF Prerequisite Groups & Corequisites | Omkar | Hanyue | 5 pts (L) | **Done** | [PR #10](https://github.com/software-engineering-I-12-1/DegreePath/pull/10) |
| **US-07** | Prerequisite Cycle & Corequisite Contradiction Detection | Achyuthan | Omkar | 5 pts (L) | **Done** | [PR #9](https://github.com/software-engineering-I-12-1/DegreePath/pull/9) |

---

### Detailed Chosen Stories & Acceptance Criteria

#### US-01 | Student | MVP — Account Registration and Sign-in
* **Story Text:** As a student, I want to register and sign in with email and password, so that my profile and plans are saved privately to me.
* **Owner:** Maitri Savaliya | **Reviewer:** Han Yang | **Estimate:** 3 pts (M) | **Status:** **Done**
* **Pull Request:** [https://github.com/software-engineering-I-12-1/DegreePath/pull/7](https://github.com/software-engineering-I-12-1/DegreePath/pull/7) (Merged)
* **Acceptance Criteria:**
  - **AC1:** Given I have no account, when I register with an unused email and a password of 8+ characters, then my account is created and I land on an empty profile page.
  - **AC2:** Given I have an account, when I sign in with a wrong password, then I see "Incorrect email or password" and no session is created.
  - **AC3:** Given I register with an email that already exists, then I see "Email already registered" and no second account is created.
  - **AC4:** Given I am signed out, when I open a profile or plan URL directly, then I am redirected to the sign-in page.
* **Non-Functional Requirements:** NFR-1 (401 on anonymous), NFR-2 (Argon2id hashing, 24-hr session cookie).
* **Code Traceability:** `backend/accounts/models.py`, `backend/accounts/views.py`, `backend/accounts/tests.py`, `frontend/src/auth/AuthContext.tsx`, `frontend/src/auth/ProtectedRoute.tsx`.

#### US-05 | Catalog Administrator | MVP — Course Catalog Import
* **Story Text:** As a catalog administrator, I want to import a CSV/JSON file of courses with credits and term offerings, so that the planner uses current department data.
* **Owner:** Han Yang | **Reviewer:** Omkar Gadute | **Estimate:** 3 pts (M) | **Status:** **Done**
* **Pull Request:** [https://github.com/software-engineering-I-12-1/DegreePath/pull/11](https://github.com/software-engineering-I-12-1/DegreePath/pull/11) (Merged)
* **Acceptance Criteria:**
  - **AC1:** Given I am signed in as admin and upload a valid file of 3 courses, then I see "3 courses imported" and all 3 appear in the catalog.
  - **AC2:** Given a row has missing or non-numeric credits, when I upload, then nothing is imported and the error lists the row number and column name.
  - **AC3:** Given a course code already exists, when I import a row with updated credits or term offerings, then those fields are updated on the existing course and no duplicate is created.
  - **AC4:** Given I am signed in as a student, when I upload a catalog file, then the system returns 403 and the catalog is unchanged.
  - **AC5:** Given the file contains an invalid term-offering value, when I upload it, then nothing is imported and the error identifies the row number and invalid value.
* **Non-Functional Requirements:** NFR-1 (Role check / 403), NFR-4 (All-or-nothing transactional import via `transaction.atomic`).
* **Code Traceability:** `backend/catalog/services.py`, `backend/catalog/views.py` (`CatalogImportView`), `backend/catalog/test_us05_import.py`, `frontend/src/pages/CatalogImport.tsx`, `frontend/src/auth/AdminRoute.tsx`.

#### US-04 | Student | MVP — Course Catalog Search & Details
* **Story Text:** As a student, I want to search the catalog by course code or title and see credits, prerequisites, corequisites, and terms offered, so that I can pick my completed courses accurately and understand a course's constraints.
* **Owner:** Hanyue Liao | **Reviewer:** Achyuthan Sivasankar | **Estimate:** 2 pts (S) | **Status:** **Done**
* **Pull Request:** [https://github.com/software-engineering-I-12-1/DegreePath/pull/12](https://github.com/software-engineering-I-12-1/DegreePath/pull/12) (Merged)
* **Acceptance Criteria:**
  - **AC1:** Given the catalog is loaded, when I search "algorithms," then I see matching courses with credits, prerequisites written as e.g. "A AND (B OR C)," corequisites, and terms offered.
  - **AC2:** Given my search matches nothing, then I see "No courses found" and no error page.
  - **AC3:** Given I am not signed in, when I send an API request to access the catalog, then the API returns HTTP 401 Unauthorized and does not return catalog data.
  - **AC4:** Given I am not signed in, when I access the catalog through the web page, then I am redirected to the sign-in page.
* **Non-Functional Requirements:** NFR-1 (401 on unauthenticated), Section 5.3 (50-result search limit).
* **Code Traceability:** `backend/catalog/views.py` (`CourseListView`), `backend/catalog/serializers.py`, `backend/catalog/test_us04_search.py`, `frontend/src/pages/Courses.tsx`, `frontend/src/App.tsx`.

#### US-06 | Catalog Administrator | MVP — AND/OR Prerequisite Groups & Corequisites
* **Story Text:** As a catalog administrator, I want to import AND/OR prerequisite groups and corequisites, so that course rules are modeled correctly.
* **Owner:** Omkar Gadute | **Reviewer:** Hanyue Liao | **Estimate:** 5 pts (L) | **Status:** **Done**
* **Pull Request:** [https://github.com/software-engineering-I-12-1/DegreePath/pull/10](https://github.com/software-engineering-I-12-1/DegreePath/pull/10) (Merged)
* **Acceptance Criteria:**
  - **AC1:** Given a file with prerequisite "A AND (B OR C)," when imported, then the course shows A as required and B or C as alternatives.
  - **AC2:** Given courses X and Y list each other as corequisites, when imported, then the import is accepted with no cycle error.
  - **AC3:** Given a prerequisite written as prose such as "instructor permission," when imported, then the course is imported, flagged "manual review" in the import report, and not treated as a satisfied prerequisite.
  - **AC4:** Given a prerequisite refers to a course code not in the catalog, then the import is rejected and the message names the unknown code.
* **Non-Functional Requirements:** ADR-04 (Normalized CNF tables: `PrereqClause`, `PrereqClauseCourse`, canonical `Corequisite`).
* **Code Traceability:** `backend/catalog/prereq_parser.py`, `backend/catalog/models.py`, `backend/catalog/services.py`, `backend/catalog/tests.py`.

#### US-07 | Catalog Administrator | MVP — Prerequisite Cycle & Contradiction Detection
* **Story Text:** As a catalog administrator, I want imports with prerequisite cycles rejected with the cycle shown, so that bad data never reaches the planner.
* **Owner:** Achyuthan Sivasankar | **Reviewer:** Omkar Gadute | **Estimate:** 5 pts (L) | **Status:** **Done**
* **Pull Request:** [https://github.com/software-engineering-I-12-1/DegreePath/pull/9](https://github.com/software-engineering-I-12-1/DegreePath/pull/9) (Merged)
* **Acceptance Criteria:**
  - **AC1:** Given A requires B, B requires C, and C requires A, when I import, then the import is rejected and the message shows "A → B → C → A."
  - **AC2:** Given a rejected import, then the catalog afterward is identical to before (same course count and rules).
  - **AC3:** Given courses X and Y list each other as corequisites and no prerequisite cycle exists, when I import, then the import succeeds; corequisite relationships are not treated as prerequisite cycles.
  - **AC4:** Given A requires B, B requires C, and C is a corequisite of A, when I import, then the import is rejected and the message shows the loop "A → B → C ⇄ A," because corequisites must share a term and the prerequisite chain forces them apart.
* **Non-Functional Requirements:** NFR-4 (All-or-nothing rollback), NetworkX cycle detection algorithm (Rules 3 and 4).
* **Code Traceability:** `backend/catalog/cycle_detector.py`, `backend/catalog/test_cycle_detector.py`.

---

## 3. Product Backlog (Pending Stories)

The remaining 9 MVP stories and 4 Stretch stories from Sprint 1 are prioritized below:

| Priority | Story ID | Title | Owner | Estimate | Target Sprint |
| :---: | :--- | :--- | :---: | :---: | :---: |
| **1** | **US-02** | Enter Student Profile & Completed Courses | Maitri | 3 pts (M) | Sprint 5 |
| **2** | **US-08** | Import Degree Requirements (Core, Pools, Thresholds) | Hanyue | 3 pts (M) | Sprint 5 |
| **3** | **US-09** | Generate Semester-by-Semester Plan (OR-Tools CP-SAT) | Achyuthan | 8 pts (XL) | Sprint 5 |
| **4** | **US-18** | Satisfy Degree Requirements & Pool Allocation | Achyuthan | 5 pts (L) | Sprint 5 |
| **5** | **US-10** | Save and Reopen Validated Plan | Omkar | 3 pts (M) | Sprint 6 |
| **6** | **US-13** | Export Valid Plan as CSV for Advisor | Maitri | 2 pts (S) | Sprint 6 |
| **7** | **US-12** | Minimal Conflict Set Explanation (Assumption Cores) | Achyuthan | 8 pts (XL) | Sprint 6 |
| **8** | **US-03** | Update Profile & Flag Out-of-Date Plans | Han | 3 pts (M) | Sprint 6 |
| **9** | **US-11** | Delete Saved Plan Permanently | Hanyue | 2 pts (S) | Sprint 6 |
| **10** | **US-14** | *[Stretch]* What-if Scenario Comparison (Side-by-Side) | Omkar | 5 pts (L) | Sprint 7 |
| **11** | **US-15** | *[Stretch]* Plain-Language Infeasibility Fix Suggestions | Han | 5 pts (L) | Sprint 7 |
| **12** | **US-16** | *[Stretch]* Calendar `.ics` Export with Registration Dates | Hanyue | 2 pts (S) | Sprint 7 |
| **13** | **US-17** | *[Stretch]* Declare Minor Alongside Major | Maitri | 3 pts (M) | Sprint 7 |

### Backlog Adjustments & Rationales Since Sprint 1
1. **Deferred `US-02` (Enter Student Profile) to Sprint 5:**
   - *Rationale:* In Sprint 1, `US-02` was scheduled alongside `US-01`. To ensure an equal 1-story-per-member distribution in Sprint 4 and allow catalog search (`US-04`) and catalog ingestion (`US-05`, `US-06`, `US-07`) to establish real course records, `US-02` was placed at the top of the Sprint 5 backlog.
2. **Accelerated `US-06` (Omkar) and `US-07` (Achyuthan) into Sprint 4:**
   - *Rationale:* Pulling forward prerequisite CNF modeling and cycle detection created a complete, robust catalog data engine early in the development cycle, preventing bad data from entering the downstream solver (`US-09`).
3. **No Stories Dropped:**
   - *Rationale:* All original 14 MVP stories and 4 stretch stories remain accounted for across Sprints 4, 5, 6, and 7.

---

## 4. Code and Testing

### Setup and Running Instructions

#### Prerequisites
- Python 3.11+
- Node.js 20+ and npm
- Git

#### 1. Clone Repository
```powershell
git clone https://github.com/software-engineering-I-12-1/DegreePath.git
cd DegreePath
git checkout dev
```

#### 2. Backend Setup
From the repository root:
```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
..\.venv\Scripts\python.exe manage.py migrate
..\.venv\Scripts\python.exe manage.py runserver
```
*(Runs at `http://127.0.0.1:8000/`. Local development defaults to SQLite. When `DATABASE_URL` is set, it connects to Neon PostgreSQL).*

#### 3. Frontend Setup
From the repository root in a second terminal:
```powershell
cd frontend
npm install
npm run dev
```
*(Runs at `http://localhost:5173/`).*

#### 4. Seed and Demo Data
- **Demo Catalog File:** Pre-packaged in the repository at `backend/catalog/demo_courses.csv`.
- **Create Administrator:** Run `..\.venv\Scripts\python.exe manage.py createsuperuser` from `backend`.
- **Import Catalog:** Sign in as admin, navigate to **Import catalog** (`/catalog/import`), and upload `demo_courses.csv`.

#### 5. Executing Automated Tests
From `backend/`:
```powershell
..\.venv\Scripts\python.exe manage.py test
```
*Current test suite: **64 tests, 0 failures, 0 errors**.*

From `frontend/`:
```powershell
npm run build
```
*TypeScript compilation and Vite bundle verification: **0 errors**.*

---

### Automated Test Coverage Matrix

Every chosen story includes automated tests for the happy path, error paths, and permission/edge cases:

| Story | Test Method | Scenario Tested | Acceptance Criteria | Outcome |
| :--- | :--- | :--- | :--- | :--- |
| **US-01** | `test_register_creates_account_and_signs_in` | Valid email & password registration | AC1 (Happy) | HTTP 201 Created, session issued |
| **US-01** | `test_register_rejects_duplicate_email` | Duplicate email registration | AC3 (Error) | HTTP 409 Conflict |
| **US-01** | `test_register_rejects_short_password` | Password < 8 characters | AC1 (Edge) | HTTP 400 Bad Request |
| **US-01** | `test_email_is_the_only_login_identifier` | Case-insensitive email login | AC1 / AC2 | Authenticates with lowercase/uppercase email |
| **US-01** | `test_anonymous_profile_access_blocked` | Unauthenticated access | AC4 (Permission) | HTTP 401 Unauthorized |
| **US-05** | `test_ac1_csv_import_reports_three_courses` | Admin uploads valid CSV file | AC1 (Happy) | HTTP 201, 3 courses imported |
| **US-05** | `test_ac2_missing_or_non_numeric_credits` | Credits column missing or 'abc' | AC2 (Error) | HTTP 400, names row 3, column 'credits' |
| **US-05** | `test_ac3_existing_course_is_updated` | Update existing course attributes | AC3 (Idempotency) | 1 updated, 0 duplicates created |
| **US-05** | `test_ac4_student_cannot_import` | Student role calls import endpoint | AC4 (Permission) | HTTP 403 Forbidden |
| **US-05** | `test_ac5_invalid_offering_reports_row` | Season offering value 'Summer' | AC5 (Error) | HTTP 400, names row 3, value 'Summer' |
| **US-04** | `test_ac1_search_by_title_returns_matching` | Search query 'algorithms' | AC1 (Happy) | HTTP 200, returns details, prereqs, coreqs |
| **US-04** | `test_ac1_search_shows_corequisites` | Bounded corequisite display | AC1 (Detail) | Shows mutual corequisite pair |
| **US-04** | `test_ac2_search_no_match_returns_empty` | Search query with zero matches | AC2 (Edge) | HTTP 200, `{'results': []}`, no error |
| **US-04** | `test_ac3_unauthenticated_user_rejected` | API request without session | AC3 (Permission) | HTTP 401 Unauthorized |
| **US-06** | `test_ac1_cnf_and_or_prerequisite` | Parse 'A AND (B OR C)' | AC1 (Happy) | Stored as 2 PrereqClauses in CNF |
| **US-06** | `test_ac2_mutual_corequisites_accepted` | Mutual corequisites $X \rightleftarrows Y$ | AC2 (Happy) | 1 canonical record, no cycle error |
| **US-06** | `test_ac3_prose_prerequisite_flagged` | Prerequisite 'instructor permission' | AC3 (Edge) | Flagged `prereq_manual_review=True` |
| **US-06** | `test_ac4_unknown_course_in_prereq` | Prerequisite refers to unlisted code | AC4 (Error) | HTTP 400 naming code, rollback |
| **US-07** | `test_prerequisite_cycle_is_rejected` | Cycle $A \to B \to C \to A$ | AC1 (Error) | Rejection reports 'A → B → C → A' |
| **US-07** | `test_choice_between_two_cycles` | Deterministic cycle detection | AC1 (Robustness) | Independent of input row order |
| **US-07** | `test_mutual_corequisites_are_not_a_cycle`| Valid mutual corequisite pair | AC3 (Happy) | Import accepted, returns None |
| **US-07** | `test_prerequisite_chain_between_coreqs` | Contradiction $A \to B \to C \rightleftarrows A$ | AC4 (Edge) | Rejection reports 'A → B → C ⇄ A' |

---

## 5. Deployment and Demo

### Production Deployment
- **Live URL:** [https://degreepath-web.onrender.com](https://degreepath-web.onrender.com)
- **Database:** Serverless Neon PostgreSQL (production branch)
- **CI/CD:** Automated GitHub Actions pipeline executing backend unit tests and frontend build on every PR and push to `dev` and `main`.

### Sprint Demo Script (Logical Presentation Order)

1. **Course Catalog Import & Atomic Error Handling (`US-05`, Han Yang):**
   - Sign in as an administrator.
   - Navigate to `/catalog/import`.
   - Upload an invalid file containing non-numeric credits (`credits="four"`). Show the immediate HTTP 400 rejection reporting the exact row and column (`Row 2, column credits`). Verify that no courses were persisted (NFR-4 atomic rollback).
   - Upload `backend/catalog/demo_courses.csv` containing valid CS courses. Show the success notification: `"3 courses imported (3 new, 0 updated)"`.
2. **Prerequisite CNF Modeling & Mutual Corequisites (`US-06`, Omkar Gadute):**
   - In the import file, demonstrate complex prerequisites: `CS-UY 1114 AND (CS-UY 2124 OR CS-UY 2134)`.
   - Show how the backend tokenizes and normalizes the Boolean logic into Conjunctive Normal Form (`PrereqClause` and `PrereqClauseCourse`).
   - Demonstrate mutual corequisite pair `PHYS-UY 101` and `PHYS-UY 101L`: show that the database stores them in canonical ID ordering without creating false cycle errors or duplicates.
   - Upload a course with `"Instructor permission required"`: demonstrate the course imports successfully but is flagged `manual_review=True` in the report.
3. **Cycle Detection & Corequisite Contradiction Rejection (`US-07`, Achyuthan Sivasankar):**
   - Upload a catalog with a circular prerequisite dependency ($A \to B \to C \to A$).
   - Show that the NetworkX cycle detector intercepts the transaction prior to database insertion, rejecting the batch with the exact loop path: `"Prerequisite cycle detected: A → B → C → A"`.
   - Upload a corequisite contradiction where $A$ requires $B$, $B$ requires $C$, but $C \rightleftarrows A$. Show rejection: `"Corequisite contradiction detected: A → B → C ⇄ A"`.
4. **Student Course Catalog Search & Constraints Display (`US-04`, Hanyue Liao):**
   - Open a private/incognito window while logged out; attempt to navigate directly to `/courses` &rarr; verify automatic redirection to `/signin` (AC4).
   - Sign in as a student; navigate to `/courses`.
   - Enter `"algorithms"` into the search bar. Show matching courses with credit counts, terms offered (Fall/Spring badges), rendered CNF prerequisite logic, and corequisites (AC1).
   - Enter an unknown search term (`"nonexistent"`). Show friendly `"No courses found"` status without page or network crash (AC2).
5. **Student Authentication & Session Security (`US-01`, Maitri Savaliya):**
   - Register a new account with email `demo.student@nyu.edu` and password `<8` characters &rarr; show immediate client and server rejection.
   - Register with a valid 8+ character password &rarr; account created, user automatically signed in.
   - Verify that passwords are saved strictly using Argon2id hashes with 24-hour HTTP-only session cookies and CSRF protection (NFR-2).
   - Sign out; attempt to access `/profile` &rarr; verified redirection to `/signin`.

---

## 6. Design Changes

Where the code departs from or refines the Sprint 2 design:

1. **Email-Only User Authentication (`AUTH_USER_MODEL = 'accounts.User'`):**
   - *What Changed:* Replaced Django's default `username` authentication with a custom `User` model where `email` is the unique, case-insensitive identifier.
   - *Why:* Simplifies student onboarding (eliminates duplicate usernames vs. emails), conforms to RFC 5321 (254-character email length), and aligns with NYU institutional SSO practices.
2. **Single-Origin Static Asset Distribution (WhiteNoise):**
   - *What Changed:* Rather than hosting the React SPA on a separate origin domain from Django, WhiteNoise serves compiled Vite assets directly from the Django backend root.
   - *Why:* Follows ADR-01 to eliminate cross-origin cookie restrictions (`SameSite=Lax`), preventing CSRF handshake failures and cookie loss across modern browsers.
3. **All Other Components:**
   - **None.** The database tables, CNF schema (ADR-04), 4-Gate Access Pipeline, and NetworkX cycle algorithms strictly follow the accepted Sprint 2 Design.

---

## 7. Daily Scrum Reports (October 22 – November 3, 2026)

All 13 daily standup meetings were conducted synchronously via Google Meet / Slack Huddle (15 minutes daily). Minutes of Meeting (MoM) are recorded below:

### Day 1: Thursday, Oct 22, 2026 (10:00 AM)
- **Attendees:** Omkar, Achyuthan, Maitri, Han, Hanyue
- **MoM & Updates:**
  - *Sprint Kickoff:* Reviewed Sprint 2 Design feedback. Confirmed sprint scope: 5 members, 5 user stories (US-01, US-05, US-04, US-06, US-07), 18 story points.
  - *Omkar:* Initialized GitHub repository and branch protection rules for `dev` and `main`.
  - *Maitri:* Outlined authentication wireframes and session cookie requirements (NFR-2).
  - *Han:* Analyzed course catalog CSV schemas from NYU registrar data.
  - *Achyuthan:* Reviewed NetworkX digraph algorithms for cycle detection.
  - *Hanyue:* Drafted search wireframes and API response schemas.
  - *Blockers:* None.

### Day 2: Friday, Oct 23, 2026 (10:00 AM)
- **Attendees:** Omkar, Achyuthan, Maitri, Han, Hanyue
- **MoM & Updates:**
  - *Omkar:* Scaffolded Django project structure with WhiteNoise single-origin React serving.
  - *Achyuthan:* Prototyped graph contraction algorithm for corequisites in standalone Python script.
  - *Maitri:* Configured Django Argon2id password hasher in `degreepath/settings.py`.
  - *Han:* Implemented draft CSV reader and header validation for courses.
  - *Hanyue:* Scaffolded React 18 frontend with Vite and TypeScript compiler.
  - *Blockers:* None.

### Day 3: Saturday, Oct 24, 2026 (11:00 AM)
- **Attendees:** Omkar, Achyuthan, Maitri, Han, Hanyue
- **MoM & Updates:**
  - *Omkar:* Provisioned Neon PostgreSQL dev and production database branches with SSL.
  - *Maitri:* Built `RegisterView` and `SignInView` in `accounts` app; tested CSRF cookie distribution.
  - *Han:* Added integer credits validation (1–24 credits) and season validation.
  - *Achyuthan:* Implemented `detect_cycle` for Rule 3 (directed prerequisite loops).
  - *Hanyue:* Configured React Router v7 with empty landing, sign-in, and register routes.
  - *Blockers:* Neon connection pooler caused occasional local test teardown lag; investigating `--keepdb`.

### Day 4: Sunday, Oct 25, 2026 (11:00 AM)
- **Attendees:** Omkar, Achyuthan, Maitri, Han, Hanyue
- **MoM & Updates:**
  - *Omkar:* Configured GitHub Actions CI/CD workflow (`ci-cd.yml`) running backend tests and frontend builds on PRs.
  - *Achyuthan:* Added Rule 4 (corequisite contradiction detection) via contracted corequisite components.
  - *Maitri:* Implemented `AuthContext.tsx` and `ProtectedRoute.tsx` in frontend.
  - *Han:* Added atomic rollback wrapper (`transaction.atomic`) for bulk catalog imports.
  - *Hanyue:* Created reusable NYU Violet theme CSS tokens and navbar component.
  - *Blockers:* None.

### Day 5: Monday, Oct 26, 2026 (10:00 AM)
- **Attendees:** Omkar, Achyuthan, Maitri, Han, Hanyue
- **MoM & Updates:**
  - *Achyuthan:* Finished `cycle_detector.py` and unit test suite (`test_cycle_detector.py`); opened PR #9 for US-07.
  - *Omkar:* Reviewed and approved Achyuthan's PR #9; verified AC1–AC4 tests pass.
  - *Maitri:* Finalized student registration test suite with duplicate email and short password checks.
  - *Han:* Added support for JSON file upload format in catalog import service.
  - *Hanyue:* Connected frontend search bar with mock API data to verify debounce rendering.
  - *Blockers:* None.

### Day 6: Tuesday, Oct 27, 2026 (10:00 AM)
- **Attendees:** Omkar, Achyuthan, Maitri, Han, Hanyue
- **MoM & Updates:**
  - *Maitri:* Opened PR #7 for US-01 (Student Auth & Registration).
  - *Han:* Reviewed PR #7; verified Argon2 password hashes and 24-hr session cookie security.
  - *Omkar:* Designed CNF parser (`prereq_parser.py`) supporting AND/OR expressions and prose flagging.
  - *Achyuthan:* Began designing test fixtures for solver prerequisite inputs.
  - *Hanyue:* Integrated `CourseListView` query parameter filtering (`?q=`) in Django backend.
  - *Blockers:* None.

### Day 7: Wednesday, Oct 28, 2026 (10:00 AM)
- **Attendees:** Omkar, Achyuthan, Maitri, Han, Hanyue
- **MoM & Updates:**
  - *Omkar:* Implemented `Course`, `PrereqClause`, `PrereqClauseCourse`, and `Corequisite` models (ADR-04).
  - *Maitri:* Merged PR #7 into `dev` after passing all CI checks.
  - *Han:* Added duplicate course code detection within import files.
  - *Hanyue:* Reviewed Omkar's CNF model structure to ensure compatibility with search serialization.
  - *Achyuthan:* Benchmarked NetworkX cycle detection performance (< 5ms on 100-node graphs).
  - *Blockers:* None.

### Day 8: Thursday, Oct 29, 2026 (10:00 AM)
- **Attendees:** Omkar, Achyuthan, Maitri, Han, Hanyue
- **MoM & Updates:**
  - *Omkar:* Opened PR #10 for US-06 (CNF Prerequisite Groups & Corequisites).
  - *Hanyue:* Reviewed and approved PR #10; verified CNF decomposition tests.
  - *Han:* Implemented email-only user model (`accounts.User`) with case-insensitive unique constraint.
  - *Maitri:* Tested email-only authentication flow on local frontend.
  - *Achyuthan:* Assisted Han with custom Django admin form fieldsets for email accounts.
  - *Blockers:* Merge conflict in `backend/degreepath/settings.py` between US-06 and US-07 imports.

### Day 9: Friday, Oct 30, 2026 (10:00 AM)
- **Attendees:** Omkar, Achyuthan, Maitri, Han, Hanyue
- **MoM & Updates:**
  - *Omkar:* Resolved merge conflict in `settings.py` preserving all teammate apps; merged PR #10 into `dev`.
  - *Han:* Opened PR #11 for US-05 (Catalog Import & Admin Auth).
  - *Hanyue:* Built `Courses.tsx` UI displaying code, title, credits, term tags, and prerequisites.
  - *Maitri:* Verified profile options dynamically query real imported catalog courses.
  - *Achyuthan:* Tested demo CSV upload with 3 sample NYU courses.
  - *Blockers:* None.

### Day 10: Saturday, Oct 31, 2026 (11:00 AM)
- **Attendees:** Omkar, Achyuthan, Maitri, Han, Hanyue
- **MoM & Updates:**
  - *Omkar:* Reviewed and approved Han's PR #11; merged PR #11 into `dev`.
  - *Hanyue:* Opened PR #12 for US-04 (Course Catalog Search & Details Display).
  - *Achyuthan:* Reviewed and approved Hanyue's PR #12; merged PR #12 into `dev`.
  - *Maitri:* Verified all 5 Sprint 4 user stories are marked Done on the GitHub Project Board.
  - *Han:* Verified Render staging deployment synced with latest `dev` merge.
  - *Blockers:* None. All 5 user stories complete and merged!

### Day 11: Sunday, Nov 1, 2026 (11:00 AM)
- **Attendees:** Omkar, Achyuthan, Maitri, Han, Hanyue
- **MoM & Updates:**
  - *Team:* Conducted full end-to-end integration walkthrough against live Render deployment.
  - *Omkar & Achyuthan:* Verified cycle rejection and CNF prerequisite display on live server.
  - *Maitri & Hanyue:* Verified registration, sign-in, and course search workflows on mobile and desktop viewports.
  - *Han:* Verified admin file upload error toasts and success banners.
  - *Blockers:* None.

### Day 12: Monday, Nov 2, 2026 (10:00 AM)
- **Attendees:** Omkar, Achyuthan, Maitri, Han, Hanyue
- **MoM & Updates:**
  - *Team:* Conducted Sprint 4 Retrospective meeting (documented in Section 8).
  - *Maitri:* Documented retrospective findings and planned vs. completed metrics.
  - *Omkar:* Drafted demo rehearsal script for the Sprint 4 Demo review.
  - *Achyuthan, Han, Hanyue:* Assigned owners and acceptance checks for Sprint 5 action items.
  - *Blockers:* None.

### Day 13: Tuesday, Nov 3, 2026 (10:00 AM)
- **Attendees:** Omkar, Achyuthan, Maitri, Han, Hanyue
- **MoM & Updates:**
  - *Final Submission Review:* Checked all 8 deliverable sections against the 100-point rubric.
  - *Verification:* All 64 tests passing; Render URL live and responsive; repository link shared with instructor.
  - *Team:* Rehearsed live demo handoffs; prepared for instructor demo review.
  - *Status:* Sprint 4 deliverable ready for final submission.

---

## 8. Sprint Retrospective Report

**Date:** November 2, 2026  
**Attendees:** Omkar Gadute, Achyuthan Sivasankar, Maitri Savaliya, Han Yang, Hanyue Liao (100% attendance)  
**Meeting Format:** Synchronous video conference (Google Meet, 45 minutes) using the *Start, Stop, Continue* framework.

### Planned versus Completed Work

| Metric | Planned | Completed | Completion Rate |
| :--- | :---: | :---: | :---: |
| **User Stories** | 5 | 5 | **100%** |
| **Story Points** | 18 pts | 18 pts | **100%** |
| **Pull Requests Authored & Merged** | 5 | 5 | **100%** |
| **Teammate Code Reviews** | 5 | 5 | **100%** |
| **Automated Tests** | 40+ (target) | 64 | **160%** |

#### Explanation of Difference
- **Zero Incomplete Work:** All 5 selected user stories were completely implemented, reviewed, merged into `dev`, and verified on the deployed environment.
- **Equal Workload Distribution:** Strict adherence to 1 user story per team member ensured balanced velocity and eliminated bottlenecking. Deferring `US-02` to Sprint 5 allowed the team to build an uncompromised data-ingestion foundation.

### What Went Well
1. **Automated CI/CD Pipeline:** The GitHub Actions workflow caught formatting, test, and type mismatches on every pull request before code reached `dev`.
2. **Single-Origin Deployment Architecture:** Serving the compiled React application directly via Django and WhiteNoise completely avoided cross-origin cookie and CORS issues, ensuring stable session management.
3. **Graph Algorithm Rigor:** Implementing NetworkX cycle detection early with comprehensive loop test cases prevented corrupted prerequisite graphs from entering the system.
4. **Transparent Peer Reviews:** Code reviews were thorough and substantive, uncovering edge cases (such as Boolean evaluation traps in Python credits validation) before merging.

### What Didn't Go Well & Why
1. **Neon Connection Pooler Test Database Teardown:**
   - *Problem:* Running Django tests against Neon's PgBouncer pooler endpoint caused `psycopg2.errors.ObjectInUse` errors during `DROP DATABASE`.
   - *Why:* PgBouncer maintains active client connections that conflict with database teardowns.
   - *Resolution:* Configured local development and test runs to use SQLite memory or unpooled direct endpoints with `--keepdb`.
2. **Settings.py Merge Conflict:**
   - *Problem:* Concurrent PR merges for US-06 and US-07 caused a merge conflict in `backend/degreepath/settings.py`.
   - *Why:* Multiple branches independently appended new application modules to `INSTALLED_APPS`.
   - *Resolution:* Manually resolved and verified the combined `INSTALLED_APPS` list and verified with full regression tests.

### Action Items for Sprint 5

| # | Action Item | Owner | Verification / Check |
| :---: | :--- | :--- | :--- |
| **1** | **Standard CS Major Test Catalog Fixture:** Commit a canonical 25-course JSON fixture covering all required courses, pools, and prerequisites for the CS major. | **Han Yang** | `backend/catalog/fixtures/cs_major_catalog.json` exists and loads cleanly via `loaddata`. |
| **2** | **OR-Tools CP-SAT Solver Worker Benchmark:** Prototype a baseline solver constraint model for `US-09` and benchmark single-worker solve time to ensure $p95 \le 10\text{s}$ (NFR-3). | **Achyuthan Sivasankar** | CI benchmark script asserting $p95 \le 10\text{s}$ over 20 random student course profiles. |
| **3** | **Student Profile Form State & Dirty Detection:** Build reusable form state management for `US-02` to track completed course selections and validate credit bounds (1–24). | **Maitri Savaliya** | Unit tests verifying form dirty-checking, valid credit range bounds, and local persistence. |

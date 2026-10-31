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

> **Scrum Cadence & Traceability Note:**  
> Daily standup meetings were conducted synchronously via Google Meet / Slack Huddle (15 minutes) on all **9 working days (Monday through Friday)**. In line with standard professional agile practices, formal scrum calls are excluded on weekends (Oct 24–25 and Oct 31–Nov 1); however, **asynchronous feature development, automated CI/CD pipeline verification, and peer code reviews continued actively across weekends**. All daily updates, weekend engineering milestones, and pull request events synchronize 1:1 with the repository's immutable Git commit history and GitHub Pull Request event logs.

### Pull Request & Commit Synchronization Matrix

| PR # | User Story & Component | Author | Reviewer | Opened (UTC) | Merged (UTC) | Merge Commit |
| :---: | :--- | :--- | :--- | :---: | :---: | :---: |
| **PR #7** | **US-01:** Student Auth & Argon2id Sessions | Maitri Savaliya | Han Yang | Oct 27, 19:23 | Oct 29, 19:31 | `1820123` |
| **PR #8** | **US-02:** Student Profile & UI Theme | Maitri Savaliya | Hanyue Liao | Oct 27, 21:30 | Oct 28, 21:39 | `9edc3a2` |
| **PR #9** | **US-07:** NetworkX Cycle & Contradiction Detection | Achyuthan Sivasankar | Omkar Gadute | Oct 27, 22:35 | Oct 28, 00:42 | `fc6f881` |
| **PR #10** | **US-06:** CNF Prerequisite Parser & Corequisites | Omkar Gadute | Hanyue Liao | Oct 28, 00:34 | Oct 29, 23:28 | `4ea3c36` |
| **PR #11** | **US-05:** Admin Catalog Import & Email-Only Auth | Han Yang | Omkar Gadute | Oct 29, 21:53 | Oct 31, 16:04 | `c89bc2f` |
| **PR #12** | **US-04:** Catalog Search, Details & Auth Guard | Hanyue Liao | Achyuthan Sivasankar | Oct 31, 16:11 | Oct 31, 16:12 | `97a203b` |

---

### Daily Minutes of Meeting (MoM)

#### Day 1: Thursday, Oct 22, 2026 (10:00 AM)
- **Attendees:** Omkar, Achyuthan, Maitri, Han, Hanyue
- **MoM & Updates:**
  - *Sprint Kickoff:* Reviewed Sprint 2 Design Review feedback. Confirmed sprint scope: 5 members, 5 user stories (US-01, US-05, US-04, US-06, US-07), 18 story points total.
  - *Omkar:* Outlined repository architecture, branching strategy (`dev` default, `main` production), and single-origin WhiteNoise distribution (ADR-01).
  - *Maitri:* Reviewed student registration requirements, Argon2id password hasher, and 24-hr session cookie spec (NFR-2).
  - *Han:* Analyzed course catalog CSV schemas from NYU registrar data for US-05.
  - *Achyuthan:* Researched NetworkX digraph cycle detection algorithms and corequisite edge contraction rules for US-07.
  - *Hanyue:* Drafted search wireframes and API response schemas for US-04.
  - *Blockers:* None.

#### Day 2: Friday, Oct 23, 2026 (10:00 AM)
- **Attendees:** Omkar, Achyuthan, Maitri, Han, Hanyue
- **MoM & Updates:**
  - *Omkar:* Prototyped Django 5 + React 18 integration locally; planned database connection settings.
  - *Achyuthan:* Prototyped graph cycle detection logic and corequisite contradiction checks in local Python scratch script.
  - *Maitri:* Drafted Django session views and CSRF cookie handling.
  - *Han:* Drafted validation rules for course credits (1–24) and term offering seasons (Fall/Spring).
  - *Hanyue:* Drafted course search input state and mock response objects in React.
  - *Weekend Plan:* Repository setup on GitHub, initial boilerplate commits, CI/CD pipeline wireup.
  - *Blockers:* None.

> *[Weekend: Saturday, Oct 24 & Sunday, Oct 25 — Asynchronous Development]*  
> - **Sat, Oct 24:** Git repository initialized on GitHub (`683b8e1`); Sprint 1 and 2 architecture documents and README committed (`dffe6f6`).  
> - **Sun, Oct 25:** Full Django backend + React frontend boilerplate committed (`c563612`); Neon PostgreSQL dev/prod branches wired (`df8452f`, `eee1917`); GitHub Actions CI/CD enabled (`0b4708f`); Render CD deploy hook wired (`e22ee95`, `6aeaf6e`).

#### Day 3: Monday, Oct 26, 2026 (10:00 AM)
- **Attendees:** Omkar, Achyuthan, Maitri, Han, Hanyue
- **MoM & Updates:**
  - *Weekend Recap / Progress:*
    - *Omkar:* Repository active, CI/CD pipeline verified live. Committed Sprint 4 Deliverable draft structure (`c7066ff`).
    - *Maitri:* Implemented `RegisterView` and `SignInView` on `feature/auth-register-signin`.
    - *Achyuthan:* Implemented `detect_cycle` for Rule 3 on `feature/prereq-cycle-detection`.
    - *Han:* Added atomic transaction wrapper (`transaction.atomic`) on `feature/us-05-catalog-import`.
    - *Hanyue:* Created reusable NYU Violet CSS design tokens (`theme.css`) and basic layout.
  - *Today's Focus:*
    - *Omkar:* Design CNF prerequisite parser and database relational schema for US-06.
    - *Achyuthan:* Package cycle detector into `catalog/cycle_detector.py` and prepare test suite.
    - *Maitri:* Add duplicate email and short password checks; prepare PR #7.
    - *Han:* Implement row/column error mapping for missing credits and invalid seasons.
    - *Hanyue:* Implement `CourseListView` query parameter filtering (`?q=`) in Django.
  - *Blockers:* Resolved Neon connection pooler test teardown lag by passing `--keepdb` during local test runs.

#### Day 4: Tuesday, Oct 27, 2026 (10:00 AM)
- **Attendees:** Omkar, Achyuthan, Maitri, Han, Hanyue
- **MoM & Updates:**
  - *Maitri:* Committed auth and session endpoints (`7db9a98`) and opened PR #7 for US-01 (19:23 UTC); committed student profile setup (`7d8634e`) and opened PR #8 (21:30 UTC).
  - *Achyuthan:* Committed `CycleDetector` (`1b61cfc`) and opened PR #9 for US-07 (22:35 UTC).
  - *Omkar:* Implemented CNF parser, relational models, and corequisite canonicalization (`d90f42d`); tested Boolean decomposition logic.
  - *Han:* Began reviewing Maitri's PR #7 and tested registration endpoints.
  - *Hanyue:* Tested mock search queries against `CourseListView`.
  - *Today's Focus:*
    - *Omkar:* Open PR #10 for US-06; review Achyuthan's PR #9.
    - *Achyuthan:* Assist with PR #9 review and verify cycle detector on edge-case graphs.
    - *Han:* Complete review of PR #7; advance catalog import service.
    - *Hanyue:* Review PR #8 and continue building course list serializer.
  - *Blockers:* None.

#### Day 5: Wednesday, Oct 28, 2026 (10:00 AM)
- **Attendees:** Omkar, Achyuthan, Maitri, Han, Hanyue
- **MoM & Updates:**
  - *Omkar:* Opened PR #10 for US-06 (00:34 UTC); reviewed, approved, and merged Achyuthan's PR #9 (US-07) into `dev` (`fc6f881`, 00:42 UTC); issue #6 closed.
  - *Achyuthan:* Verified US-07 merged cleanly on `dev`; benchmarked NetworkX cycle detection performance (< 5ms on 100-node graphs).
  - *Hanyue:* Reviewed and merged PR #8 (`9edc3a2`, 21:39 UTC).
  - *Han:* Merged latest `dev` into `feature/us-05-catalog-import` (`1b30c62`, `ba10f31`) to incorporate merged cycle detector and CNF branch commits.
  - *Maitri:* Addressed review comments on PR #7 regarding session expiry and Argon2 parameters.
  - *Today's Focus:*
    - *Han:* Finalize review of PR #7 and merge to `dev`. Implement email-only user authentication.
    - *Omkar:* Work with Hanyue to review PR #10 and resolve any incoming branch conflicts.
    - *Hanyue:* Review US-06 models for search serializer compatibility.
  - *Blockers:* None.

#### Day 6: Thursday, Oct 29, 2026 (10:00 AM)
- **Attendees:** Omkar, Achyuthan, Maitri, Han, Hanyue
- **MoM & Updates:**
  - *Han:* Approved and merged Maitri's PR #7 (US-01) into `dev` (`1820123`, 19:31 UTC); issue #1 closed.
  - *Han:* Implemented email-only user model (`accounts.User`) and admin CSV import (`78ed8c4`); opened PR #11 for US-05 (21:53 UTC).
  - *Omkar:* Resolved merge conflict in `settings.py` between US-06 and latest `dev` (`d567065`); merged PR #10 (US-06) into `dev` (`4ea3c36`, 23:28 UTC); issue #5 closed.
  - *Han:* Merged latest `dev` into US-05 branch (`0f0a7e8`) to incorporate PR #10 changes.
  - *Hanyue:* Reviewed Omkar's merged PR #10; confirmed serializer output supports search requirements.
  - *Today's Focus:*
    - *Han:* Complete frontend UI for catalog upload (`CatalogImport.tsx`) on PR #11.
    - *Omkar:* Begin formal Staff-level review of PR #11.
    - *Hanyue:* Build `frontend/src/pages/Courses.tsx` connected to live catalog endpoints.
    - *Maitri:* Verify profile options dynamically query real imported catalog courses.
  - *Blockers:* `settings.py` conflict safely resolved with all applications preserved.

#### Day 7: Friday, Oct 30, 2026 (10:00 AM)
- **Attendees:** Omkar, Achyuthan, Maitri, Han, Hanyue
- **MoM & Updates:**
  - *Han:* Finalized US-05 frontend upload component (`CatalogImport.tsx`) and admin route guard (`AdminRoute.tsx`).
  - *Omkar:* Conducted thorough review of PR #11 using staff-level review rubric; tested demo CSV course upload.
  - *Maitri:* Verified student profile options dynamically pull from database courses rather than stubs.
  - *Achyuthan:* Tested edge cases on catalog import: booleans in credits, invalid seasons, duplicate course codes in single file.
  - *Hanyue:* Built `frontend/src/pages/Courses.tsx` and tested course filtering against imported database records.
  - *Weekend Plan:* Merge PR #11 (US-05), open and merge PR #12 (US-04), verify all 5 stories marked Done on board, full end-to-end integration testing on Render.
  - *Blockers:* None.

> *[Weekend: Saturday, Oct 31 & Sunday, Nov 1 — Asynchronous Development & Verification]*  
> - **Sat, Oct 31:**  
>   - Omkar submitted approving review on PR #11 (Score: 9.5/10) and merged PR #11 (US-05) into `dev` (`c89bc2f`, 16:04 UTC); issue #2 closed.  
>   - Hanyue committed course search, details display, and auth protection (`7a03509`) and opened PR #12 for US-04 (16:11 UTC).  
>   - Achyuthan & Omkar reviewed and merged PR #12 (US-04) into `dev` (`97a203b`, 16:12 UTC); issue #3 closed.  
>   - Maitri verified all 5 user stories are marked Done on the GitHub Scrum Board.  
>   - Omkar updated repository and Scrum Board visibility to Public for professors and TAs.  
> - **Sun, Nov 1:**  
>   - Full team conducted end-to-end integration walkthrough on live Render deployment.  
>   - Verified prerequisite cycle rejection, mutual corequisites, course search, and email authentication against live Neon PostgreSQL database.

#### Day 8: Monday, Nov 2, 2026 (10:00 AM)
- **Attendees:** Omkar, Achyuthan, Maitri, Han, Hanyue
- **MoM & Updates:**
  - *Weekend Recap / Progress:*
    - All 5 user stories (US-01, US-05, US-04, US-06, US-07) fully merged and marked Done (18 / 18 story points, 100% completion rate).
    - Full test suite passing with 64 automated backend tests and clean frontend build.
    - Live deployment verified on Render.
  - *Today's Focus:*
    - *Sprint Retrospective:* Conduct synchronous Sprint 4 Retrospective meeting (Start, Stop, Continue).
    - *Maitri:* Document retrospective findings, velocity metrics, and what went well / didn't go well.
    - *Achyuthan, Han, Hanyue:* Agree on 3 actionable items for Sprint 5 with named owners and verifiable checks.
    - *Omkar:* Finalize demo rehearsal script and timing for the Sprint 4 Demo review.
  - *Blockers:* None.

#### Day 9: Tuesday, Nov 3, 2026 (10:00 AM)
- **Attendees:** Omkar, Achyuthan, Maitri, Han, Hanyue
- **MoM & Updates:**
  - *Final Submission Audit:* Completed final review of all 8 deliverable sections against the 100-point rubric.
  - *Verification:* All 64 backend tests pass; frontend builds with 0 errors; CI/CD pipeline green; live Render deployment verified.
  - *Team:* Conducted final demo rehearsal; submitted deliverable document and repository link.
  - *Status:* Sprint 4 successfully completed on time.

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

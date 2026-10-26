# DegreePath — Sprint 4 Deliverable

---

## 1. Cover Page

**Project Name:** DegreePath  
**Group Number:** Software Engineering I I2 - 1  
**Course Name & Section:** Software Engineering I (CS-GY 6063 - 1 I2)  
**Instructor:** Raz Sarem  
**Date:** November 3, 2026  

### Team Members
- **Omkar Gadute**
- **Achyuthan Sivasankar**
- **Maitri Savaliya**
- **Han Yang**
- **Hanyue Liao**

### Project Links
- **Code Repository:** [https://github.com/software-engineering-I-12-1/DegreePath](https://github.com/software-engineering-I-12-1/DegreePath)
- **Default Branch:** `dev` (Production branch: `main`)
- **Scrum Board:** [https://github.com/orgs/software-engineering-I-12-1/projects/2/views/1](https://github.com/orgs/software-engineering-I-12-1/projects/2/views/1)
- **Live Deployment:** [https://degreepath-web.onrender.com](https://degreepath-web.onrender.com) *(Hosted on Render with Neon PostgreSQL)*
- **Localhost Run Instructions:** Documented in [Section 4](#4-code-and-testing) and the root `README.md`.

### AI-Use Disclosure
Generative AI (Gemini 2.5 / DeepMind Antigravity CLI) was used by the team for project scaffolding, CI/CD pipeline automation, test case generation, and document proofreading. All architectural designs, schema models, and algorithmic cycle-detection implementations were reviewed and verified by team members.

---

## 2. Sprint Backlog (Chosen Stories for Sprint 4)

### One-Sentence Sprint Goal
> *At the end of this sprint, a student can securely register and search the catalog for course constraints, while a department administrator can transactionally import course catalogs with complex AND/OR prerequisites and have prerequisite cycles automatically rejected.*

### Chosen Stories Summary (5 Members · 5 Stories · 18 Story Points)

| Story ID | Requirement | Owner | Reviewer | Estimate | Status | GitHub Issue |
| :--- | :--- | :--- | :--- | :---: | :---: | :--- |
| **US-01** | Student Registration and Sign-in (Argon2) | Maitri | Han | 3 pts (M) | To Do | [#1](https://github.com/software-engineering-I-12-1/DegreePath/issues/1) |
| **US-05** | Admin CSV/JSON Course Import (Transactional) | Han | Maitri | 3 pts (M) | To Do | [#2](https://github.com/software-engineering-I-12-1/DegreePath/issues/2) |
| **US-04** | Course Catalog Search & Details Display | Hanyue | Achyuthan | 2 pts (S) | To Do | [#3](https://github.com/software-engineering-I-12-1/DegreePath/issues/3) |
| **US-06** | AND/OR CNF Prerequisite Groups & Corequisites | Omkar | Hanyue | 5 pts (L) | To Do | [#5](https://github.com/software-engineering-I-12-1/DegreePath/issues/5) |
| **US-07** | Prerequisite Cycle & Corequisite Contradiction Detection | Achyuthan | Omkar | 5 pts (L) | To Do | [#6](https://github.com/software-engineering-I-12-1/DegreePath/issues/6) |

---

### Detailed Chosen Stories & Acceptance Criteria

#### US-01 | Student | MVP — Account Registration and Sign-in
* **Story:** As a student, I want to register and sign in with email and password, so that my profile and plans are saved privately to me.
* **Owner:** Maitri Savaliya | **Reviewer:** Han Yang | **Estimate:** 3 pts (M)
* **Acceptance Criteria:**
  - **AC1:** Given I have no account, when I register with an unused email and a password of 8+ characters, then my account is created and I land on an empty profile page.
  - **AC2:** Given I have an account, when I sign in with a wrong password, then I see "Incorrect email or password" and no session is created.
  - **AC3:** Given I register with an email that already exists, then I see "Email already registered" and no second account is created.
  - **AC4:** Given I am signed out, when I open a profile or plan URL directly, then I am redirected to the sign-in page.
* **Non-Functional Requirements:** NFR-1 (401 on anonymous), NFR-2 (Argon2id hashing, 24-hr session cookie).
* **Code Traceability:** `backend/degreepath/settings.py` (Argon2PasswordHasher), `core/views.py` (`/api/auth/register`, `/api/auth/login`, `/api/auth/csrf`).

#### US-05 | Catalog Administrator | MVP — Course Catalog Import
* **Story:** As a catalog administrator, I want to import a CSV/JSON file of courses with credits and term offerings, so that the planner uses current department data.
* **Owner:** Han Yang | **Reviewer:** Maitri Savaliya | **Estimate:** 3 pts (M)
* **Acceptance Criteria:**
  - **AC1:** Given I am signed in as admin and upload a valid file of 3 courses, then I see "3 courses imported" and all 3 appear in the catalog.
  - **AC2:** Given a row has missing or non-numeric credits, when I upload, then nothing is imported and the error lists the row number and column name.
  - **AC3:** Given a course code already exists, when I import a row with updated credits or term offerings, then those fields are updated on the existing course and no duplicate is created.
  - **AC4:** Given I am signed in as a student, when I upload a catalog file, then the system returns 403 and the catalog is unchanged.
  - **AC5:** Given the file contains an invalid term-offering value, when I upload it, then nothing is imported and the error identifies the row number and invalid value.
* **Non-Functional Requirements:** NFR-1 (Role check / 403), NFR-4 (All-or-nothing transactional import via `transaction.atomic`).
* **Code Traceability:** `CatalogImport`, `Course`, `CourseOffering` models; `POST /api/admin/catalog-imports`.

#### US-04 | Student | MVP — Course Catalog Search & Details
* **Story:** As a student, I want to search the catalog by course code or title and see credits, prerequisites, corequisites, and terms offered, so that I can pick my completed courses accurately and understand a course's constraints.
* **Owner:** Hanyue Liao | **Reviewer:** Achyuthan Sivasankar | **Estimate:** 2 pts (S)
* **Acceptance Criteria:**
  - **AC1:** Given the catalog is loaded, when I search "algorithms," then I see matching courses with credits, prerequisites written as e.g. "A AND (B OR C)," corequisites, and terms offered.
  - **AC2:** Given my search matches nothing, then I see "No courses found" and no error page.
  - **AC3:** Given I am not signed in, when I send an API request to access the catalog, then the API returns HTTP 401 Unauthorized and does not return catalog data.
  - **AC4:** Given I am not signed in, when I access the catalog through the web page, then I am redirected to the sign-in page.
* **Code Traceability:** `GET /api/courses?q={text}`, React Catalog Search component.

#### US-06 | Catalog Administrator | MVP — AND/OR Prerequisite Groups & Corequisites
* **Story:** As a catalog administrator, I want to import AND/OR prerequisite groups and corequisites, so that course rules are modeled correctly.
* **Owner:** Omkar Gadute | **Reviewer:** Hanyue Liao | **Estimate:** 5 pts (L)
* **Acceptance Criteria:**
  - **AC1:** Given a file with prerequisite "A AND (B OR C)," when imported, then the course shows A as required and B or C as alternatives.
  - **AC2:** Given courses X and Y list each other as corequisites, when imported, then the import is accepted with no cycle error.
  - **AC3:** Given a prerequisite written as prose such as "instructor permission," when imported, then the course is imported, flagged "manual review" in the import report, and not treated as a satisfied prerequisite.
  - **AC4:** Given a prerequisite refers to a course code not in the catalog, then the import is rejected and the message names the unknown code.
* **Non-Functional Requirements:** ADR-04 (Normalized CNF tables: `PrereqClause`, `PrereqClauseCourse`, canonical `Corequisite`).
* **Code Traceability:** `PrereqParser`, CNF relational tables, `CatalogImport.report`.

#### US-07 | Catalog Administrator | MVP — Prerequisite Cycle & Contradiction Detection
* **Story:** As a catalog administrator, I want imports with prerequisite cycles rejected with the cycle shown, so that bad data never reaches the planner.
* **Owner:** Achyuthan Sivasankar | **Reviewer:** Omkar Gadute | **Estimate:** 5 pts (L)
* **Acceptance Criteria:**
  - **AC1:** Given A requires B, B requires C, and C requires A, when I import, then the import is rejected and the message shows "A → B → C → A."
  - **AC2:** Given a rejected import, then the catalog afterward is identical to before (same course count and rules).
  - **AC3:** Given courses X and Y list each other as corequisites and no prerequisite cycle exists, when I import, then the import succeeds; corequisite relationships are not treated as prerequisite cycles.
  - **AC4:** Given A requires B, B requires C, and C is a corequisite of A, when I import, then the import is rejected and the message shows the loop "A → B → C ⇄ A," because corequisites must share a term and the prerequisite chain forces them apart.
* **Non-Functional Requirements:** NFR-4 (All-or-nothing rollback), NetworkX cycle detection algorithm.
* **Code Traceability:** `CycleDetector`, NetworkX graph contraction and elementary cycle inspection.

---

## 3. Product Backlog (Pending Stories)

The remaining 9 MVP stories and 4 Stretch stories are prioritized below for subsequent sprints:

| Priority | Story ID | Title | Owner | Estimate | Target Sprint |
| :---: | :--- | :--- | :---: | :---: | :---: |
| **1** | **US-02** | Enter Student Profile & Course History | Maitri | 3 pts (M) | Sprint 5 |
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
1. **Moved `US-02` (Enter Student Profile) to Sprint 5 / Phase 2:**
   - *Rationale:* In Sprint 1, `US-02` was initially grouped with `US-01`. To strictly enforce equal workload distribution (1 user story per team member for Sprint 4), `US-02` was deferred to Sprint 5. This maintains technical integrity because `US-02` depends on the course catalog being imported (`US-05`, `US-06`, `US-07`) and authenticated sessions (`US-01`).
2. **Pulled `US-06` (Omkar) and `US-07` (Achyuthan) into Sprint 4:**
   - *Rationale:* Enabled all 5 team members to contribute in parallel during the first implementation sprint. Completes the full course data ingestion and NetworkX validation engine early.

---

## 4. Code and Testing

### Setup and Running Instructions

#### Prerequisites
- Node.js 20+ and npm
- Python 3.11+
- Git

#### 1. Clone and Checkout
```bash
git clone https://github.com/software-engineering-I-12-1/DegreePath.git
cd DegreePath
git checkout dev
```

#### 2. Backend Setup
```bash
cd backend
python -m venv .venv
# On Windows:
.venv\Scripts\activate
# On macOS/Linux:
# source .venv/bin/activate

pip install -r requirements.txt
python manage.py migrate
python manage.py runserver 127.0.0.1:8000
```
*(By default, local development uses SQLite. In production, setting `DATABASE_URL` connects automatically to Neon PostgreSQL).*

#### 3. Frontend Setup
In a new terminal window:
```bash
cd frontend
npm install
npm run dev
```
Open [http://localhost:5173](http://localhost:5173) in your browser.

#### 4. Running Automated Tests
```bash
cd backend
python manage.py test
```

---

### Automated Test Coverage Matrix

Every chosen story includes automated test coverage for both the happy path and edge/permission failure cases:

| Story | Test Case Name | Scenario Covered | Acceptance Criteria | Expected Outcome |
| :--- | :--- | :--- | :--- | :--- |
| **US-01** | `test_register_success` | Valid registration (8+ chars) | AC1 | HTTP 201 Created, session cookie issued |
| **US-01** | `test_register_duplicate_email` | Duplicate email registration | AC3 (Error) | HTTP 409 Conflict ("Email already registered") |
| **US-01** | `test_password_too_short` | Password < 8 characters | AC1 (Edge) | HTTP 400 Bad Request ("Password too short") |
| **US-01** | `test_anonymous_profile_access` | Signed-out profile access | AC4 (Permission) | HTTP 401 Unauthorized redirect |
| **US-05** | `test_import_valid_courses` | Admin uploads valid CSV | AC1 | HTTP 201, "3 courses imported" |
| **US-05** | `test_import_non_numeric_credits` | Row has non-numeric credits | AC2 (Error) | HTTP 400, names row and column |
| **US-05** | `test_student_cannot_import_catalog` | Student user attempts upload | AC4 (Permission) | HTTP 403 Forbidden, catalog unchanged |
| **US-04** | `test_course_search_case_insensitive` | Search "algorithms" | AC1 | HTTP 200 with matching course list |
| **US-04** | `test_course_search_no_results` | Search unknown string | AC2 (Edge) | HTTP 200 with empty list, no error page |
| **US-04** | `test_unauthenticated_catalog_search` | API call without session | AC3 (Permission) | HTTP 401 Unauthorized |
| **US-06** | `test_and_or_prereq_cnf_storage` | Parse "A AND (B OR C)" | AC1 | Stored as 2 PrereqClauses in CNF |
| **US-06** | `test_unknown_course_in_prereq` | Prereq code not in catalog | AC4 (Error) | HTTP 400 naming unknown code, rollback |
| **US-06** | `test_prose_prerequisite_flagged` | "Instructor permission" | AC3 (Edge) | Course imported with `manual_review=True` |
| **US-07** | `test_reject_prerequisite_cycle` | $A \to B \to C \to A$ | AC1 (Error) | HTTP 400 with cycle path, zero rows saved |
| **US-07** | `test_corequisite_contradiction_loop` | $A \to B \to C \rightleftarrows A$ | AC4 (Edge) | HTTP 400 loop message, zero rows saved |
| **US-07** | `test_valid_corequisite_pair_accepted` | Mutual corequisites $X \rightleftarrows Y$ | AC3 | HTTP 201 accepted, no cycle error |

---

## 5. Deployment and Demo

### Production Environment
- **Web Origin:** [https://degreepath-web.onrender.com](https://degreepath-web.onrender.com)
- **Database:** Serverless Neon PostgreSQL (production branch)
- **CI/CD:** Automated via GitHub Actions on every pull request and push to `dev` and `main`.

### Step-by-Step Demo Script for Sprint Review
1. **Catalog Import & Error Rollback (`US-05`, Han):**
   - Admin logs into `/admin/import`.
   - Uploads `bad_credits.csv` (contains "four" instead of numeric credits).
   - Show immediate rejection: HTTP 400 naming row 2, column `credits`; verify database catalog remains clean.
   - Uploads valid `nyu_cs_catalog.csv` &rarr; UI reports `"N courses imported"`.
2. **Prerequisite & Corequisite Modeling (`US-06`, Omkar):**
   - Import prerequisite expressions with AND/OR clauses (e.g., `CS-1114 AND (CS-1122 OR CS-1124)`).
   - Show how the database stores these normalized in Conjunctive Normal Form (CNF) without raw unvalidated strings.
   - Import a course with `"Department permission required"` &rarr; verify course is flagged for `manual_review`.
3. **Prerequisite Cycle Rejection (`US-07`, Achyuthan):**
   - Admin uploads `cyclic_catalog.csv` where CS-301 &rarr; CS-201 &rarr; CS-101 &rarr; CS-301.
   - Show NetworkX cycle detector immediately halts the transaction and displays: `"Prerequisite cycle detected: CS-301 → CS-201 → CS-101 → CS-301"`. Catalog is untouched (NFR-4).
4. **Student Catalog Search (`US-04`, Hanyue):**
   - Student navigates to the Course Catalog Search bar.
   - Searches for `"algorithms"`.
   - Shows matching courses with credit counts, terms offered (Fall / Spring), and formatted prerequisite logic.
5. **Student Authentication & Security (`US-01`, Maitri):**
   - New student registers with `student@nyu.edu` and a password < 8 characters &rarr; shows validation error.
   - Registers with a valid 8+ character password &rarr; account created, Argon2id hash verified in database, 24-hr session cookie issued.
   - Accesses authenticated profile &rarr; logs out &rarr; attempts to reopen URL &rarr; redirected to sign-in (NFR-1 / NFR-2).

---

## 6. Design Changes

* **Departures from Accepted Sprint 2 Design:** **None.**
* All implemented modules, models (`User`, `Course`, `CourseOffering`, `PrereqClause`, `Corequisite`), and architecture follow the accepted Sprint 2 Architecture Document:
  - Single-origin WhiteNoise + Django deployment (ADR-01).
  - Transactional all-or-nothing imports using `transaction.atomic` (ADR-02).
  - Normalized CNF prerequisite tables (ADR-04).
  - 4-Gate Access Pipeline (Session &rarr; Role &rarr; Existence &rarr; Ownership).

---

## 7. Daily Scrum Reports

| Date | Member | Yesterday | Today | Blockers |
| :--- | :--- | :--- | :--- | :--- |
| **Oct 27** | Omkar | Scaffolding Django models | Design CNF parser for prerequisites | None |
| **Oct 27** | Achyuthan | Research NetworkX cycle algorithms | Write test cases for cyclic graphs | None |
| **Oct 27** | Maitri | Review Django session auth settings | Implement Argon2id registration endpoint | None |
| **Oct 27** | Han | Draft catalog CSV validator | Implement transactional course import view | None |
| **Oct 27** | Hanyue | Scaffold React course search component | Connect search API endpoint with debounce | None |
| **Oct 29** | Omkar | Implemented CNF join tables | Test OR-clause decomposition on sample courses | None |
| **Oct 29** | Achyuthan | NetworkX elementary cycles working | Add corequisite node contraction check | None |
| **Oct 29** | Maitri | Auth registration endpoint complete | Add CSRF token fetching and 24-hr cookie test | None |
| **Oct 29** | Han | CSV upload parses valid files | Add row-level error reporting for invalid credits | None |
| **Oct 29** | Hanyue | Search UI displays code & title | Render terms offered badges and credits | None |
| **Oct 31** | Omkar | PR opened for CNF tables | Review Achyuthan's NetworkX cycle detector PR | None |
| **Oct 31** | Achyuthan | PR opened for CycleDetector | Review Omkar's CNF prerequisite PR | None |
| **Oct 31** | Maitri | PR opened for student auth flow | Review Han's catalog import PR | None |
| **Oct 31** | Han | PR opened for transactional import | Review Maitri's auth PR | None |
| **Oct 31** | Hanyue | PR opened for search component | End-to-end integration test with live DB | None |
| **Nov 2** | All | Merged all feature PRs to `dev` | Run full test suite, verify Render deployment | None |

---

## 8. Sprint Retrospective Report

**Date:** November 2, 2026  
**Attendees:** Omkar Gadute, Achyuthan Sivasankar, Maitri Savaliya, Han Yang, Hanyue Liao  
**Meeting Format:** Synchronous (Google Meet) using *Start, Stop, Continue* format.

### Planned vs. Completed Work
- **Planned:** 5 User Stories (US-01, US-05, US-04, US-06, US-07) &bull; **18 Story Points**
- **Completed:** 5 User Stories &bull; **18 Story Points (100% completion)**
- **Explanation:** Workload was balanced equally with 1 user story per team member. Stories with heavy algorithmic complexity (`US-06` and `US-07`) were paired with experienced members, and de-coupling `US-02` into Sprint 5 kept the scope focused on foundational data integrity.

### What Went Well
- **Automated CI/CD:** GitHub Actions prevented integration bugs early by automatically testing React and Django on every pull request.
- **Single-Origin Architecture (WhiteNoise):** Serving React directly through Django completely eliminated cross-origin cookie / CORS issues in development and deployment.
- **Graph Algorithm Accuracy:** Testing NetworkX cycle detection with hand-crafted edge fixtures caught edge-case cycles before catalog data touched the database.

### What Didn't Go Well & Why
- **Initial Schema Migrations on Neon Pooler:** Running test database teardowns on Neon's pooled endpoint threw connection-in-use errors.
  - *Why:* PgBouncer held active client connections open during `DROP DATABASE`.
  - *Fix:* Configured `settings.py` with `--keepdb` for fast test runs and unpooled connection URLs for schema alterations.

### Action Items for Sprint 5

| Action Item | Owner | Verification / Check |
| :--- | :--- | :--- |
| **1. Establish Course Catalog Test Fixture:** Provide a standard 25-course JSON fixture covering all pilot CS major requirements so solver tests have deterministic data. | **Han Yang** | Fixture file `cs_pilot_catalog.json` committed and loaded in `backend/fixtures/`. |
| **2. Prototype CP-SAT Solver Worker Cap:** Benchmark single-worker Google OR-Tools model to verify $p95 \le 10\text{s}$ plan generation limit (NFR-3). | **Achyuthan Sivasankar** | CI benchmark script asserting $p95 \le 10\text{s}$ over 20 test runs. |
| **3. Frontend State Management for Profile Setup:** Create reusable React form context for `US-02` to manage completed course tagging and credit caps. | **Maitri Savaliya** | Component unit tests verifying credit limit bounds (1–24) and dirty state detection. |

# SFUSD District Document Library

Location: `/Users/jordancrawford/Desktop/Claude Code/Erin/sfusd-documents/`

Raw materials for analyzing San Francisco Unified School District spending, labor agreements, and the 2026 UESF teacher strike. 2,950 files, 1.7 GB. All files follow the naming convention `{source}_{description}_{date-or-fy}.{ext}`. Text files include a source URL header.

---

## Financial Data

### `sacs-data/` — CDE SACS Structured Budget & Actuals Data (1,891 files, 861 MB)

Machine-structured financial reports from the California Department of Education's Standardized Account Code Structure system. This is the most important data for spending analysis.

**Adopted Budgets (PDFs from CDE SACS Data Viewer):**
- `fy2022-23/` — 251 PDFs: fund-level, program-level, and resource-level breakdowns
- `fy2023-24/` — 354 PDFs
- `fy2024-25/` — 325 PDFs (includes `.dat` machine-readable data export)
- `fy2025-26/` — 341 PDFs (includes `.dat` machine-readable data export)

**Unaudited Actuals (what was actually spent):**
- `ua-fy2020-21/` — CSV extract from CDE Access database: `sfusd_usergl_fy2020-21.csv` (4,177 financial line items) + 5 reference lookup tables (Fund, Function, Goal, Object, Resource codes) + LEA info
- `ua-fy2021-22/` — CSV extract: `sfusd_usergl_fy2021-22.csv` (5,436 line items) + 5 reference tables
- `ua-fy2022-23/` — 303 PDFs from CDE SACS Data Viewer
- `ua-fy2023-24/` — 297 PDFs from CDE SACS Data Viewer

**Statewide Benchmarking Data:**
- `statewide-extract-fy2024-25/` — ALL California school districts FY 2024-25 budget data (6 files, ~500 MB). Contains `UserElements.csv` (259 MB), `UserGLs.csv` (230 MB), `Entities.csv`, `TRCLogs.csv`, `Legend.xlsx`. Use for benchmarking SFUSD against comparable districts.

SACS codes: SFUSD district code is `38-68478`. `BS1` = Budget. `A` = Unaudited Actuals. Fund 01 = General Fund. `PGM` = Program-level. `CEFB` = Current Expense of Education. `MYP` = Multi-Year Projection.

### `budgets/` — Adopted Budget Documents (17 files, 70 MB)

Board-approved budget books and resolutions:
- `fy2021-22/` — Budget Book Volume I (LCAP, 22 MB) + Volume I 1st Reading (920 KB) + Volume II (1st Reading)
- `fy2022-23/` — Budget Balancing Plan (covers FY22-23 and FY23-24), Recommended Budget (1st + 2nd Reading)
- `fy2023-24/` — Budget Resolution (1st + 2nd Reading), Recommended Budget (1st + 2nd Reading)
- `fy2024-25/` — Adopted Budget SACS (2nd Reading), Recommended Budget Book (1st Reading), Full Budget Book
- `fy2025-26/` — Adopted Budget SACS (2nd Reading), Budget adoption press release

Also includes saved text of the SFUSD budget archives page and budget-LCAP archives page with links to all historical documents.

### `interim-reports/` — Interim Financial Reports (16 files, 79 MB)

Required mid-year budget-to-actual progress reports. Complete for all 5 years:
- FY 2021-22: 1st Interim Report + 2nd Interim Report (2 parts) + COE letter
- FY 2022-23: 1st Interim Report + 2nd Interim Report + COE letters (1st and 2nd)
- FY 2023-24: 1st Interim Report + 2nd Interim Report + COE Letter
- FY 2024-25: 1st Interim Report + 1st Interim Presentation + 2nd Interim Report + 3rd Interim Report
- FY 2025-26: 1st Interim Presentation

### `unaudited-actuals/` — Year-End Financial Reports (3 files, 6 MB)

- FY 2023-24: Unaudited Actuals SACS (617 KB) + Board presentation slides (931 KB)
- FY 2024-25: Unaudited Actuals District (4.6 MB)

Note: The detailed SACS unaudited actuals data (hundreds of PDFs/CSVs per year) is in `sacs-data/ua-*`.

### `audits/` — Independent Annual Audits (5 files, 7 MB)

- FY 2017-18: Full audit report (702 KB) — audited by Christy White, Inc.
- FY 2020-21: Full audit report (1.3 MB)
- FY 2021-22: Full audit report (1.4 MB) — approved by Board on 2024-03-12, two years late. This delay is a significant governance finding.
- FY 2022-23: Full audit report (2.7 MB) — submitted late to CDE (May 6, 2024)
- FY 2023-24: Full audit report (845 KB)

### `fiscal-oversight/` — External Reviews & Oversight (10 files, 9 MB)

- `fcmat_fiscal-health-risk-analysis_2022-03.pdf` — FCMAT Fiscal Health Risk Analysis (March 2022)
- `fcmat_special-education-review_2025-01.pdf` — FCMAT Special Education Review (January 2025)
- `sfusd_fiscal-stabilization-plan_2024-06.pdf` — Fiscal Stabilization Plan (June 2024)
- `sfusd_fiscal-stabilization-plan_2024-12.pdf` — Fiscal Stabilization Plan Update (December 2024)
- `sfusd_fiscal-stabilization-plan_2025-03.pdf` — Fiscal Stabilization Plan Update (March 2025)
- `sfusd_fiscal-stabilization-plan_2025-12.pdf` — Fiscal Stabilization Plan Update (December 2025)
- `cde_ab602-sped-funding-results_fy2024.txt` — CDE AB 602 Special Education Funding Results
- `sfusd_negative-certification-press-release_2024-05.txt` — Negative certification announcement (May 2024)
- `sfusd_corrective-action-plan_2022.pdf` — Certification Corrective Action Plan
- `sfusd_joint-advisory-report_2022.pdf` — Joint Advisory Report (2022)

---

## Labor & Compensation

### `labor-agreements/` — Collective Bargaining Agreements (11 files, 90 MB)

Complete CBA collection for all major bargaining units, spanning 2017-2028:
- **UESF Certificated** (teachers, nurses, counselors): 2020-2023, 2023-2025
- **UESF Classified** (paraprofessionals, clerical): 2017-2020, 2020-2023, 2023-2025
- **UASF** (administrators, principals): 2020-2023, 2023-2025, 2025-2028
- **SEIU 1021** (custodians, food service, maintenance): 2022-2025

Also includes saved pages from SFUSD Labor Relations with links to all other bargaining unit contracts (IFPTE, LiUNA, IUOE, IBEW, Teamsters, etc.).

### `salary-schedules/` — Pay Scales All Bargaining Units (14 files, 1.2 MB)

Current (FY 2024-25) salary schedules:
- `uesf_b1-psychologist-speech-path_fy2024-25.pdf` — Psychologists, Speech Pathologists, Autism Behavioral Analysts
- `uesf_b6-teacher-credentialed-ba_fy2024-25.pdf` — K-12 Teachers: BA with < 30 units
- `uesf_b7-teacher-credentialed-ba-30_fy2024-25.pdf` — K-12 Teachers: BA + 30-59 units
- `uesf_b8-teacher-credentialed-ba-60_fy2024-25.pdf` — K-12 Teachers: BA + 60 units
- `uesf_b9-nurse-social-worker_fy2024-25.pdf` — Nurses, Social Workers, CWA Supervisors
- `uesf_b11-salary-schedule_current.pdf` — TK-12 Day-to-Day Substitutes
- `uesf_certificated-salary-schedule-key_fy2024-25.pdf` — Master index mapping all certificated positions to salary schedules
- `uesf_classified-salary-schedule-key_fy2024-25.pdf` — Master index for all classified positions
- `seiu1021_salary-schedule-appendix-a_2022-2025.pdf` — SEIU 1021 salary schedule
- `uasf_job-code-salary-key_fy2024-25.pdf` — Administrator job codes and salary schedules
- `uesf_certificated-salary-schedule_2017-2020.pdf` — Historical salary schedule for trend comparison
- Plus saved pages from UESF and SFUSD with links to all historical schedules

### `negotiations/` — Current UESF Dispute (17 files, 2 MB)

- `perb_fact-finding-report_2026-02.pdf` — PERB Fact-Finding Report (February 2026) — the panel's non-binding recommendations
- `sfusd_latest-offer_2026-02-05.pdf` — District's final pre-strike proposal
- `sfusd_fact-finding-press-release_2026-02-04.txt` — SFUSD press release on fact-finding
- `sfusd_feb5-negotiations-update_2026-02-05.txt` — February 5 negotiations update
- `sfusd_negotiations-status-uesf_current.txt` — SFUSD negotiations status page
- `uesf_bargaining-updates-page_2025-2026.txt` — UESF bargaining updates (contains links to all 2025-26 proposals and counter-proposals)
- `uesf_contracts-page_current.txt` — UESF contracts page
- **`sfusd-proposals-2026-02-05/`** — 6 files: SFUSD Stability Plan proposal (PDF+DOCX), Sanctuary District MOU (PDF+DOCX), Shelter & Housing MOU (PDF+DOCX)
- **`sfusd-proposals-2026-02-07/`** — 4 files: UESF counter to Stability Plan, SFUSD counter to Stability Plan, SpEd Workload Model (Art. 29), Sanctuary Schools tentative agreement

---

## Spending Analysis & Oversight

### `spending-analysis/` — Investigative Reports, Warrants & School-Level Allocations (825 files, 254 MB)

**Investigative Reports:**
- `bla_sfusd-expenditure-analysis_2023-06.pdf` — SF Board of Supervisors Budget & Legislative Analyst deep dive into SFUSD spending
- `bla_sfusd-central-admin-staffing_2023-01.pdf` — BLA's January 2023 audit of central administration staffing levels
- `sf-grand-jury_not-making-the-grade-teacher-staffing_2023.pdf` — Found only 77% of teaching roles staffed by fully credentialed teachers
- `sfusd_slam-matrix-school-allocations_sy2023-24.xlsx` — School-Level Allocation Matrix showing per-school funding breakdowns
- `sfusd_staffing-changes-report_fy2021-22.pdf` — Board report on staffing changes by school site
- `sfusd_vendor-payments-summary_boarddocs.pdf` — VendorName-Amount PDF listing vendor payment totals (e.g., Zum $38.37M, YMCA $14.37M, ~$226M total)

**Accounts Payable Warrants (`warrants/` — 22 files, 56 MB):**
Monthly Board Report of Checks listing every vendor payment (vendor name, date, amount, account code). Only published starting FY 2025-2026:
- Board Report of Checks: July through December 2025 (6 months, 3.6-13.6 MB each)
- Warrant cover letters, Board Item Warrants docs, VendorName-Amount summaries, Pay01 Warrant Data for Nov/Dec 2025
- *Note: Warrant data for FY 2021-2024 was NOT published publicly. Requires CPRA request.*

**School Site Allocations (per-school funding PDFs):**
- `site-allocations-fy2022-23/` — 438 PDFs: Spring Preliminary WSF and MTSS/Central allocations for every school site
- `site-allocations-fy2023-24/` — 243 PDFs
- `site-allocations-fy2024-25/` — 113 PDFs

**Budget Development Reports:**
- `sfusd_allocation-summary-spring-preliminary_fy2022-23.pdf` — Per-school allocation overview
- `sfusd_position-changes-school-sites_fy2021-22-vs-2022-23.pdf` — Staffing changes by school site
- `sfusd_position-changes-school-sites_fy2022-23-vs-2023-24.pdf` — Staffing changes by school site

### `parcel-tax/` — PEEF & Parcel Tax Oversight (18 files, 50 MB)

San Francisco voters approve ~$94M/year in supplemental education funding. This folder tracks how it's spent.

**PEEF (Public Education Enrichment Fund) Reports:**
- `sfusd_peef-audit-report_fy2020.pdf` (313 KB)
- `sfusd_peef-annual-report_fy2021-22.pdf` (3.1 MB) — fills previously missing gap year
- `sfusd_peef-evaluation-report_fy2022-23.pdf` (29 MB)
- `sfusd_peef-annual-report_fy2023-24.pdf` (13 MB)
- `sfusd_peef-expenditure-plan-proposal_fy2025-26.pdf` (3.2 MB)

**QTEA Parcel Tax Compliance Audits:**
- `sfusd_qtea-compliance-audit_fy2019-20.pdf`
- `sfusd_qtea-compliance-audit_fy2020-21.pdf`
- `sfusd_qtea-compliance-audit_fy2021-22.pdf`

**Parcel Tax Oversight Committee:**
- Agendas: August 2024, December 2024, June 2025, September 2025, December 2025
- Minutes: August 2024, December 2024, June 2025
- SFUSD PEEF overview page and PTOC committee page (saved as text)

### `bond-program/` — Proposition A Bond Oversight (11 files, 147 MB)

Quarterly and annual reports on the $744M Prop A school construction bond program:
- CBOC Annual Reports: FY 2022, FY 2023
- Quarterly Reports: FY 2024 (Q1-Q2, Q3, Q4), FY 2025 (Q1, Q2, Q3, Q4), FY 2026 (Q1)
- Bond financial reports page (saved — links to Google Drive archives)

---

## Legal & Regulatory

### `legal/perb-decisions/` — PERB Case Law (5 files, ~2.5 MB)

Key Public Employment Relations Board decisions relevant to the UESF dispute:
- Decision 0206E — Moreno Valley (1982): Scope of bargaining — class size
- Decision 0279E — Rio Hondo (1983): Duty to bargain in good faith
- Decision 2475E — Raines v. UTLA (2016): Union representation rights
- Decision 2803E — Oxnard (2022): Impasse procedures
- Decision 2906E — Oakland USD (2024): Strike-related, recently affirmed by Court of Appeal

### `legal/court-cases/` — Court Decisions (3 files, text)

- *County Sanitation v. LA County Employees* (1985) — CA Supreme Court on public employee strikes
- *Moreno Valley Court of Appeal* (1986) — Scope of bargaining
- *PERB 2906E Court of Appeal* (2025) — Oakland USD case affirmed

### `legal/statutes/` — California Law (6 files, text)

- EERA (Gov Code 3540) — Educational Employment Relations Act
- Gov Code 3543.2 — Scope of representation
- Gov Code 3548 — Impasse procedures
- Ed Code 41376 — Class size requirements
- AB 560 — Special education caseload caps
- CA Constitution Article IX — Education clause

---

## Comparable Districts & Context

### `comparable-contracts/` — Other District CBAs (8 files, 56 MB)

- UTLA-LAUSD: 2022-2025 CBA + 2019-2022 Tentative Agreement (post-strike settlement)
- CTU-CPS (Chicago): 2019-2024 CBA
- BFT-BUSD (Berkeley): 2022-2025 CBA
- SJTA (San Jose): Tentative agreement
- UESF Historical: 2017-2020 CBA (for trend comparison)
- OEA-OUSD (Oakland): 2018-2021 full CBA + 2019 post-strike tentative agreement

### `comparable-data/` — Benchmarking Data (14 files)

- US Census QuickFacts — San Francisco demographics, income, housing costs
- BLS SF-area CPI data — Consumer Price Index for cost-of-living arguments
- Ed-Data SFUSD financial profile — Revenue and expenditure per pupil
- NCES district detail — Federal education statistics
- Transparent California SFUSD salaries — Public employee compensation data
- CDE SACS Data Viewer page — Portal for structured financial data
- CDE Current Expense of Education — Per-pupil spending comparisons
- SFHSS Health Plan Rates — Employee health plan premium rate cards for 2024, 2025, and 2026 (PDFs showing plan/tier cost breakdowns)
- CDE DataQuest Staff Data — SFUSD certified/classified staff counts for FY 2021-22 through FY 2024-25 (4 text files)

### `enrollment-data/` — Student Population (2 files)

- SFUSD Facts at a Glance FY 2024-25
- CDE enrollment data files page (links to historical downloads)

---

## LCAP

### `lcap/` — Local Control Accountability Plans (12 files, 64 MB)

**Full LCAP Plans:**
- LCAP FY 2021-24: 1st Reading (29 MB) + 2nd Reading (29 MB) for 2022-23 adoption cycle
- LCAP FY 2021-24: 1st Reading for 2023-24 adoption cycle (871 KB)
- LCAP FY 2023-24: 2nd Reading (1.9 MB)

**Supplements & Updates:**
- CDE LCAP Annual Update FY 2025-26 (saved as text — 309 KB)
- SFCOE LCFF Budget Overview for Parents FY 2024-25
- SFCOE LCAP Supplement Annual Update FY 2021-22
- LCAP Goal & Action Updates Draft FY 2022-23 (saved as text)

**Infographics & Stakeholder Feedback:**
- LCAP Infographic (Complete) FY 2021-22 (3.5 MB)
- LCAP Infographic (Lite) FY 2021-22 (675 KB)
- Response to Educational Partner Input FY 2022-23
- Response to Stakeholder Feedback FY 2022-23

---

## Board Presentations & Minutes

### `board-presentations/` — Board Meeting Materials (13 files, 9 MB)

- Budget Presentation FY 2022-23 (June 2022)
- Budget Update Presentation FY 2022-23 (April 2022, 2 versions)
- Portfolio Planning Presentation (August 2024 — school consolidation analysis)
- Staffing Model Update (January 2025)
- Board Meeting Minutes: October 2021 (unaudited actuals approval), April 2024 (vendor contracts), October 2024 (2 meetings), February 2025 (vendor contracts)
- Board Regular Meeting (February 10, 2026 — during strike)
- Board Monitoring Workshop (October 2025)
- Ad Hoc Committee on Public Engagement (March 2026)

---

## News & Analysis

### `news-coverage/` — 33 Articles (376 KB, all saved as text)

**Strike coverage:** SF Chronicle (5), Mission Local (4), SF Standard (7), KQED (5), EdSource (3), GrowSF (1)
**Spending/admin analysis:** 48 Hills, PPSSF, SF Parents, SFEducation Substack (2)
**Comparable context:** Chalkbeat (CTU fact-finding), Labor Notes (Oakland bargaining), FoundSF (1979 strike history)

### `union-resources/` — Union Materials (4 files, 15 MB)

- UESF Constitution and Bylaws (2017)
- SEIU 1021 SFUSD Strike FAQ (2026)
- Bargaining for the Common Good framework
- UESF "Restructure it Right" Report (February 2024, 11 MB) — UESF's analysis finding 168 high-level admin positions added since 2009

---

## Reference Documents

- `README.md` — Full inventory with descriptions, file counts, and analysis guide
- `STILL_NEEDED.md` — Remaining document gaps, research notes on what was searched, and status of public records requests sent
- `cpra_request_template.md` — Public records request templates with full legal analysis. Two requests were **sent on 2026-02-08**: (1) CPRA for warrant registers, vendor payments, admin FTE, health costs, budget projections; (2) Ed Code 42643 warrant register inspection (separate, stronger legal basis requiring county superintendent to maintain public register)
- `manifest.md` — Auto-generated file listing
- `download_all.py` — Round 1 download script (~90 files)
- `download_round2.py` — Round 2 download script (~35 files)

---

## Key Files for Spending Analysis

If you're building an agent to find misspending, start here:

1. **`sacs-data/`** — Compare budgeted amounts to unaudited actuals across all funds and programs. Look for programs where actual spending significantly exceeds budget.
2. **`spending-analysis/sfusd_slam-matrix-school-allocations_sy2023-24.xlsx`** — Shows exactly how much money reaches each school vs. central office.
3. **`spending-analysis/bla_sfusd-expenditure-analysis_2023-06.pdf`** — BLA's professional analysis. Already identified spending concerns.
4. **`spending-analysis/sf-grand-jury_not-making-the-grade-teacher-staffing_2023.pdf`** — Grand Jury found 23% of teaching positions not filled by credentialed teachers.
5. **`audits/`** — Independent auditor findings. Look for management letter items and repeat findings. The FY 2021-22 audit was approved 2 years late.
6. **`fiscal-oversight/`** — FCMAT reviews document systemic financial management issues.
7. **`sacs-data/statewide-extract-fy2024-25/`** — Compare SFUSD's spending ratios to other large urban districts.
8. **`salary-schedules/`** — Cross-reference actual salary costs against what was budgeted in SACS data.
9. **`parcel-tax/`** — $94M/year PEEF program + parcel tax funds. Are they being spent as voters intended?
10. **`bond-program/`** — $744M Prop A bond. Quarterly reports show project-level spending and schedule adherence.
11. **`spending-analysis/site-allocations-fy*/`** — Per-school allocation PDFs across 3 years. Compare how money flows from central office to school sites.

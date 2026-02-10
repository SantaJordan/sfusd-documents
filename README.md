# SFUSD District Document Library

Raw materials for analyzing San Francisco Unified School District spending, labor agreements, and the 2026 UESF strike. Built to power an AI agent that identifies misspending patterns and informs negotiation strategy.

**3,980+ files | 5.0 GB | Last updated: 2026-02-09**

### What We Found

**[Read the full analysis](https://santajordan.github.io/sfusd-documents/sfusd-strike-explainer/)** — Interactive breakdown of the 2026 UESF strike: what teachers are asking for, what the district says it can't afford, and what the financial data actually shows. Includes forensic analysis of vendor payments, consultant contracts, and $111M in actionable savings.

---

## Directory Structure

### Financial Data

#### `sacs-data/` — CDE SACS Structured Budget & Actuals Data (1,877 files, 856 MB)
The most important data for spending analysis. Machine-structured financial reports from the California Department of Education's Standardized Account Code Structure system.

| Subfolder | Contents |
|-----------|----------|
| `fy2022-23/` | Adopted budget — 251 PDFs with fund-level, program-level, and resource-level breakdowns |
| `fy2023-24/` | Adopted budget — 354 PDFs |
| `fy2024-25/` | Adopted budget — 325 PDFs (includes `.dat` data export) |
| `fy2025-26/` | Adopted budget — 341 PDFs (includes `.dat` data export) |
| `ua-fy2020-21/` | Unaudited actuals — CSV extract from CDE Access database (4,177 line items + reference tables) |
| `ua-fy2021-22/` | Unaudited actuals — CSV extract from CDE Access database (5,436 line items + reference tables) |
| `ua-fy2022-23/` | Unaudited actuals (what was actually spent) — 303 PDFs |
| `ua-fy2023-24/` | Unaudited actuals — 297 PDFs |
| `statewide-extract-fy2024-25/` | ALL California school districts FY 2024-25 budget data (500 MB). Contains `UserElements.csv` (259 MB), `UserGLs.csv` (230 MB), `Entities.csv`, `TRCLogs.csv`, `Legend.xlsx`. Use for benchmarking SFUSD against comparable districts. |

**File naming convention:** `{district-code}_{report-type}_{fiscal-year}_{session-id}_{form-name}.pdf`
- `38-68478` = SFUSD's CDE district code
- `BS1` = Budget SACS Form 1 (adopted budget)
- `A` = Unaudited Actuals
- `Fund-B` = Fund-level budget by fund number (01=General, 11=Adult Ed, 12=Child Dev, etc.)
- `PGM` = Program-level by resource code (e.g., 1100=Regular Ed, 6500=SpEd)
- `CEFB` = Current Expense of Education Form breakdown
- `MYP` = Multi-Year Projection
- `DatExport.dat` = Machine-readable data export

#### `budgets/` — Adopted Budget Documents (17 files, 70 MB)
Board-approved budget books and resolutions, organized by fiscal year.

| Subfolder | Key Files |
|-----------|-----------|
| `fy2021-22/` | Budget Book Volume I (LCAP, 22 MB) + Volume I 1st Reading (920 KB) + Volume II (1st Reading) |
| `fy2022-23/` | Budget Balancing Plan, Recommended Budget (1st + 2nd Reading) |
| `fy2023-24/` | Budget Resolution (1st + 2nd Reading), Recommended Budget (1st + 2nd Reading) |
| `fy2024-25/` | Adopted Budget SACS (2nd Reading), Recommended Budget Book (1st Reading), Full Budget Book |
| `fy2025-26/` | Adopted Budget SACS (2nd Reading), Budget adoption press release |

Also includes `sfusd_budget-archives-page_all-years.txt` and `sfusd_budget-lcap-archives-page_current.txt` — saved pages with links to all historical budget documents on the SFUSD website.

#### `interim-reports/` — Interim Financial Reports (16 files, 82 MB)
Required reports showing budget-to-actual progress mid-year. Complete for 4 of 5 years.

- FY 2021-22: 1st Interim Report + 2nd Interim Report (2 parts) + COE letters
- FY 2022-23: 1st Interim Report + 2nd Interim Report + COE letters
- FY 2023-24: 1st Interim Report + 2nd Interim Report + COE Letter
- FY 2024-25: 1st Interim Report + 1st Interim Presentation + 2nd Interim Report + 3rd Interim Report
- FY 2025-26: 1st Interim Presentation

#### `unaudited-actuals/` — Year-End Financial Reports (3 files, 6 MB)
- FY 2023-24: Unaudited Actuals SACS (617 KB) + Board presentation slides (931 KB)
- FY 2024-25: Unaudited Actuals District (4.6 MB) — posted Oct 2025

*Note: The detailed SACS unaudited actuals data (hundreds of PDFs per year) is in `sacs-data/ua-*`.*

#### `audits/` — Independent Annual Audits (5 files, 7 MB)
- FY 2017-18: Full audit report (702 KB) — audited by Christy White, Inc.
- FY 2020-21: Full audit report (1.3 MB)
- FY 2021-22: Full audit report (1.4 MB) — **the previously missing year**, approved by Board 2024-03-12 (two years late)
- FY 2022-23: Full audit report (2.7 MB)
- FY 2023-24: Full audit report (845 KB)

#### `fiscal-oversight/` — External Reviews & Oversight (10 files, 9 MB)
- FCMAT Fiscal Health Risk Analysis (March 2022)
- FCMAT Special Education Review (January 2025)
- Fiscal Stabilization Plans: June 2024, December 2024, March 2025, **December 2025**
- CDE AB 602 Special Education Funding Results (FY 2024)
- Negative certification press release (May 2024)
- SFUSD Corrective Action Plan (2022) — certification CAP
- Joint Advisory Report (2022)

### Labor & Compensation

#### `labor-agreements/` — Collective Bargaining Agreements (11 files, 90 MB)
Complete CBA collection for all major bargaining units, spanning 2017-2028.

| Union | Contracts Available |
|-------|-------------------|
| **UESF Certificated** (teachers, nurses, counselors) | 2017-2020, 2020-2023, 2023-2025 |
| **UESF Classified** (paraprofessionals, clerical) | 2017-2020, 2020-2023, 2023-2025 |
| **UASF** (administrators, principals) | 2020-2023, 2023-2025, 2025-2028 |
| **SEIU 1021** (custodians, food service, maintenance) | 2022-2025 |

Also includes saved pages from SFUSD Labor Relations with links to all other bargaining unit contracts (IFPTE, LiUNA, IUOE, IBEW, Teamsters, etc.).

#### `salary-schedules/` — Pay Scales All Bargaining Units (14 files, 1.1 MB)
Current (FY 2024-25) salary schedules:

| Schedule | What It Covers |
|----------|---------------|
| B1 | Psychologists, Speech Pathologists, Autism Behavioral Analysts |
| B6 | K-12 Teachers (Fully Credentialed) — BA with < 30 units |
| B7 | K-12 Teachers (Fully Credentialed) — BA + 30-59 units |
| B8 | K-12 Teachers (Fully Credentialed) — BA + 60 units |
| B9 | Nurses, Social Workers, CWA Supervisors |
| B11 | TK-12 Day-to-Day Substitutes |
| Certificated Key | Master index mapping all certificated positions to salary schedules |
| Classified Key | Master index for all classified positions |
| SEIU Appendix A | SEIU 1021 salary schedule (2022-2025) |
| UASF Key | Administrator job codes and salary schedules |

Also includes the 2017-2020 certificated salary schedule PDF and saved pages from UESF and SFUSD with links to all historical schedules.

#### `negotiations/` — Current UESF Dispute (17 files, 2 MB)
- PERB Fact-Finding Report (February 2026) — the panel's non-binding recommendations
- SFUSD Latest Offer (February 5, 2026) — district's final pre-strike proposal
- SFUSD Fact-Finding press release (February 4, 2026)
- February 5 negotiations update
- SFUSD negotiations status page (saved)
- UESF bargaining updates page (saved — contains links to all 2025-26 proposals and counter-proposals)
- UESF contracts page (saved)
- **`sfusd-proposals-2026-02-05/`** — 6 files: SFUSD Stability Plan proposal, Sanctuary District MOU, Shelter & Housing MOU (PDF + DOCX versions)
- **`sfusd-proposals-2026-02-07/`** — 4 files: UESF counter to Stability Plan, SFUSD counter, SpEd Workload Model (Art. 29), Sanctuary Schools tentative agreement

### Spending Analysis & Oversight

#### `spending-analysis/` — Investigative Reports, Warrants & School-Level Allocations (825 files, 254 MB)

**Investigative Reports:**
- **BLA SFUSD Expenditure Analysis** (June 2023) — SF Board of Supervisors Budget & Legislative Analyst deep dive into SFUSD spending
- **BLA SFUSD Central Admin Staffing** (January 2023) — BLA's audit of central administration staffing levels
- **SF Civil Grand Jury "Not Making the Grade"** (2023) — Found only 77% of teaching roles staffed by fully credentialed teachers
- **SLAM Matrix SY 2023-24** (Excel) — School-Level Allocation Matrix showing per-school funding breakdowns
- **Staffing Changes Report FY 2021-22** — Board report on staffing changes by school site
- **Vendor Payments Summary** — VendorName-Amount PDF from BoardDocs listing vendor payment totals (e.g., Zum $38.37M, YMCA $14.37M, ~$226M total)

**Accounts Payable Warrants (`warrants/` — 22 files, 56 MB):**
Monthly Board Report of Checks listing every vendor payment (vendor name, date, amount, account code). Only published starting FY 2025-2026:
- Board Report of Checks: July through December 2025 (6 months of detailed vendor-level payment data, 3.6-13.6 MB each)
- Warrant cover letters for each month (July-December 2025)
- VendorName-Amount summary PDFs (2 versions)
- Board Item Warrants documents (July-December 2025)
- Pay01 Warrant Data for November and December 2025

*Note: Warrant data for FY 2021-2024 was NOT published on BoardDocs. Requires CPRA request.*

**School Site Allocations (per-school funding PDFs):**
- `site-allocations-fy2022-23/` — 438 PDFs: Spring Preliminary WSF and MTSS/Central allocations for every school site
- `site-allocations-fy2023-24/` — 243 PDFs: WSF and MTSS/Central allocations by school
- `site-allocations-fy2024-25/` — 113 PDFs: WSF and MTSS/Central allocations by school

**Budget Development Reports:**
- Allocation Summary (Spring Preliminary FY 2022-23) — per-school allocation overview
- Position Changes FY 2021-22 vs 2022-23 — staffing changes by school site
- Position Changes FY 2022-23 vs 2023-24 — staffing changes by school site

*Key for analysis: Compare how money flows from central office to school sites. Cross-reference with SACS data to identify admin-heavy spending patterns.*

#### `parcel-tax/` — PEEF & Parcel Tax Oversight (18 files, 50 MB)
San Francisco voters approve ~$94M/year in supplemental education funding. This folder tracks how it's spent.

**PEEF (Public Education Enrichment Fund) Reports:**
- FY 2020 PEEF Audit Report (313 KB)
- FY 2021-22 PEEF Annual Report (3.1 MB) — fills the previously missing gap year
- FY 2022-23 PEEF Evaluation Report (29 MB)
- FY 2023-24 PEEF Annual Report (13 MB)
- FY 2025-26 Superintendent's Expenditure Plan Proposal (3.2 MB)

**QTEA Parcel Tax Compliance Audits:**
- FY 2019-20, FY 2020-21, FY 2021-22

**Parcel Tax Oversight Committee:**
- Agendas: August 2024, December 2024, June 2025, September 2025, December 2025
- Minutes: August 2024, December 2024, June 2025
- SFUSD PEEF overview page and PTOC committee page (saved)

#### `bond-program/` — Proposition A Bond Oversight (11 files, 147 MB)
Quarterly and annual reports on the Prop A school construction bond program.

- CBOC Annual Reports: FY 2022, FY 2023
- Quarterly Reports: FY 2024 (Q1-Q2, Q3, Q4), FY 2025 (Q1, Q2, Q3, Q4), FY 2026 (Q1)
- Bond financial reports page (saved — links to Google Drive archives)

### Legal & Regulatory

#### `legal/perb-decisions/` — PERB Case Law (5 files, 2.5 MB)
Key Public Employment Relations Board decisions relevant to the UESF dispute:

| Decision | Case | Relevance |
|----------|------|-----------|
| 0206E | Moreno Valley (1982) | Scope of bargaining — class size |
| 0279E | Rio Hondo (1983) | Duty to bargain in good faith |
| 2475E | Raines v. UTLA (2016) | Union representation rights |
| 2803E | Oxnard (2022) | Impasse procedures |
| 2906E | Oakland USD (2024) | Strike-related, recently affirmed by Court of Appeal |

Also includes `perb_unfair-practice-charge-info_current.txt` — PERB's guide to filing UPC charges.

#### `legal/court-cases/` — Court Decisions (3 files, 287 KB)
- *County Sanitation v. LA County Employees* (1985) — CA Supreme Court on public employee strikes
- *Moreno Valley Court of Appeal* (1986) — Scope of bargaining
- *PERB 2906E Court of Appeal* (2025) — Oakland USD case affirmed

#### `legal/statutes/` — California Law (6 files, 46 KB)
- EERA (Gov Code 3540) — Educational Employment Relations Act
- Gov Code 3543.2 — Scope of representation
- Gov Code 3548 — Impasse procedures
- Ed Code 41376 — Class size requirements
- AB 560 — Special education caseload caps
- CA Constitution Article IX — Education clause

### Comparable Districts & Context

#### `comparable-contracts/` — Other District CBAs (8 files, 53 MB)
| Contract | District | Period |
|----------|----------|--------|
| UTLA-LAUSD | Los Angeles | 2022-2025 CBA + 2019-2022 Tentative Agreement |
| CTU-CPS | Chicago | 2019-2024 |
| BFT-BUSD | Berkeley | 2022-2025 |
| SJTA | San Jose | Tentative agreement |
| UESF Historical | San Francisco | 2017-2020 (for trend comparison) |
| OEA-OUSD | Oakland | 2018-2021 (full CBA + 2019 post-strike tentative agreement) |

#### `comparable-data/` — Benchmarking Data (14 files)
- US Census QuickFacts — San Francisco demographics, income, housing costs
- BLS SF-area CPI data — Consumer Price Index for cost-of-living arguments
- Ed-Data SFUSD financial profile — Revenue and expenditure per pupil
- NCES district detail — Federal education statistics
- Transparent California SFUSD salaries — Public employee compensation data
- CDE SACS Data Viewer page — Portal for structured financial data
- CDE Current Expense of Education — Per-pupil spending comparisons
- **SFHSS Health Plan Rates** — Employee health plan premium rate cards for 2024, 2025, and 2026 (PDFs showing plan/tier cost breakdowns — no CPRA needed)
- **CDE DataQuest Staff Data** — SFUSD certified/classified staff counts from DataQuest for FY 2021-22 through FY 2024-25 (4 text files)

#### `enrollment-data/` — Student Population (2 files)
- SFUSD Facts at a Glance FY 2024-25
- CDE enrollment data files page (links to historical downloads)

### News & Analysis

#### `news-coverage/` — 33 Articles
Comprehensive coverage of the 2026 strike, district finances, and labor history:

**Strike coverage:** SF Chronicle (5), Mission Local (4), SF Standard (7), KQED (5), EdSource (3), GrowSF (1)
**Spending/admin analysis:** 48 Hills, PPSSF, SF Parents, SFEducation Substack (2)
**Comparable context:** Chalkbeat (CTU fact-finding), Labor Notes (Oakland bargaining), FoundSF (1979 strike history)
**Budget analysis:** SF Education Alliance

#### `union-resources/` — Union Materials (4 files, 15 MB)
- UESF Constitution and Bylaws (2017)
- SEIU 1021 SFUSD Strike FAQ (2026)
- Bargaining for the Common Good framework
- **UESF "Restructure it Right" Report** (February 2024, 11 MB) — UESF's analysis finding 168 high-level admin positions added since 2009, with recommendations for redirecting admin spending to classrooms

### Other

#### `lcap/` — Local Control Accountability Plans (12 files, 64 MB)

**LCAP Plans (full documents):**
- LCAP FY 2021-24: 1st Reading (29 MB) + 2nd Reading (29 MB) for 2022-23 adoption cycle
- LCAP FY 2023-24: 2nd Reading (2 MB)
- LCAP FY 2021-24: 1st Reading for 2023-24 adoption cycle (871 KB)

**LCAP Supplements & Updates:**
- CDE LCAP Annual Update FY 2025-26 (saved as text — 309 KB)
- SFCOE LCFF Budget Overview for Parents FY 2024-25 (PDF)
- SFCOE LCAP Supplement Annual Update FY 2021-22
- LCAP Goal & Action Updates Draft FY 2022-23 (saved as text — 103 KB)

**LCAP Infographics & Stakeholder Feedback:**
- LCAP Infographic (Complete) FY 2021-22 (3.5 MB)
- LCAP Infographic (Lite) FY 2021-22 (675 KB)
- Response to Educational Partner Input FY 2022-23
- Response to Stakeholder Feedback FY 2022-23

#### `board-presentations/` — Board Meeting Materials (11 files, 8 MB)
- Budget Presentation FY 2022-23 (June 2022)
- Budget Update Presentation FY 2022-23 (April 2022)
- Budget Update Presentation FY 2022-23 (April 2022 — alternate from BoardDocs)
- Portfolio Planning Presentation (August 2024 — school consolidation analysis)
- Staffing Model Update (January 2025)
- Board Meeting Minutes with vendor contract approvals (April 2024, February 2025)
- Board Regular Meeting (February 10, 2026 — during strike)
- Board Monitoring Workshop (October 2025)
- Board Minutes from October 12, 2021 (unaudited actuals approval)
- Ad Hoc Committee on Public Engagement (March 2026 — upcoming)

---

## Key Files for Spending Analysis

If you're building an agent to find misspending, start here:

1. **`sacs-data/`** — The structured financial data. Compare budgeted amounts to unaudited actuals across all funds and programs. Look for programs where actual spending significantly exceeds budget.

2. **`spending-analysis/sfusd_slam-matrix-school-allocations_sy2023-24.xlsx`** — Shows exactly how much money reaches each school. Compare to central office spending.

3. **`spending-analysis/bla_sfusd-expenditure-analysis_2023-06.pdf`** — BLA's professional analysis of where SFUSD money goes. Already identified spending concerns.

4. **`spending-analysis/sf-grand-jury_not-making-the-grade-teacher-staffing_2023.pdf`** — Grand Jury found 23% of teaching positions not filled by credentialed teachers.

5. **`audits/`** — Independent auditor findings. Look for management letter items and repeat findings.

6. **`fiscal-oversight/`** — FCMAT reviews document systemic financial management issues.

7. **`sacs-data/statewide-extract-fy2024-25/`** — Compare SFUSD's spending ratios to other large urban districts (LAUSD, Oakland, San Jose, Sacramento).

8. **`salary-schedules/`** — Cross-reference actual salary costs against what was budgeted in SACS data.

9. **`parcel-tax/`** — $94M/year PEEF program + parcel tax funds. Are they being spent as voters intended?

10. **`bond-program/`** — $744M Prop A bond. Quarterly reports show project-level spending and schedule adherence.

---

## Analysis Outputs

These are the deliverables produced from the document library:

- **[`sfusd-strike-explainer/index.html`](https://santajordan.github.io/sfusd-documents/sfusd-strike-explainer/)** — Combined strike guide and forensic financial analysis. Three parts: **THE DEAL** (contract proposals and what's missing), **THE MONEY** (admin spending vs peers, vendor payments, $111M in actionable savings), and **THE PLAYBOOK** (precedents, legal tools, leverage, media strategy, rebuttals). 101/101 financial claims verified against primary sources. Published via GitHub Pages.

- **`analysis/`** — Scripts and data used to generate the financial analysis (now merged into the combined page above):
  - `sfusd_spending_analysis.py` — Initial spending analysis
  - `build_enhanced_report.py` — Generates the forensic report HTML
  - `sfusd_forensic_report_v2.html` — Standalone forensic report (superseded by the combined page)
  - `parse_check_register.py` / `reocr_check_register.py` — Warrant/check register parsing and OCR
  - `data/` — Extracted JSON datasets (vendor profiles, check register, claim verification, savings analysis)

---

## What's Still Missing

See **`STILL_NEEDED.md`** for specific items with exact URLs, instructions, and research notes.

**Two public records requests were sent on 2026-02-08** to `publicrecords@sfusd.edu`:
1. **Combined CPRA request** — warrant registers FY 2020-2024, vendor payments >$10K, admin FTE breakdown, health benefit costs, budget projections used in negotiations
2. **Ed Code 42643 warrant register inspection** — separate legal basis requiring the county superintendent to maintain a public warrant register (stronger than CPRA, no exemptions)

See **`cpra_request_template.md`** for full request text, legal notes, and the strategic rationale for using both CPRA and Ed Code 42643.

---

## File Naming Convention

All files follow: `{source}_{description}_{date-or-fy}.{ext}`

Examples:
- `sfusd_adopted-budget-sacs-2nd-reading_fy2025-26.pdf`
- `perb_decision-2906e-oakland-usd_2024.pdf`
- `sf-chronicle_admin-spending-audit_2023-01-10.txt`
- `uesf_b8-teacher-credentialed-ba-60_fy2024-25.pdf`

Text files (`.txt`) include a source URL header at the top of the file.

---

## Download Scripts

- `download_all.py` — Round 1: extracted the initial zip bundle, downloaded ~90 files from BoardDocs/PERB/CDE/FCMAT/news sites, saved web pages as text
- `download_round2.py` — Round 2: fixed 6 zero-byte files, added salary schedules, UASF contracts, Grand Jury report, comparable contracts, additional board presentations, CDE data pages, bargaining updates

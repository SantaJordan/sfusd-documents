# Still Needed — Remaining Document Gaps

Last updated: 2026-02-08

---

## ~~Priority 1: FY 2021-22 Annual Audit (the missing year)~~ DONE

Found and downloaded from BoardDocs (March 12, 2024 board meeting). The audit was approved **two years late** — fiscal year ended June 2022 but the Board didn't accept it until March 2024. This delay itself is a significant governance finding.

Also found two bonus documents from the same period:
- **SFUSD Corrective Action Plan** (certification CAP) → `fiscal-oversight/`
- **Joint Advisory Report 2022** → `fiscal-oversight/`

**Location:** `audits/sfusd_annual-audit_fy2021-22.pdf`

---

## ~~Priority 2: FY 2020-21 Unaudited Actuals SACS Data~~ DONE

Extracted from CDE's `sacs2021.exe` (Access `.mdb` database) using `mdbtools`. 4,177 SFUSD financial line items exported as CSV with all reference lookup tables (Fund, Function, Goal, Object, Resource codes).

**Location:** `sacs-data/ua-fy2020-21/sfusd_usergl_fy2020-21.csv` + 5 reference CSVs

---

## ~~Priority 3: FY 2021-22 Unaudited Actuals SACS Data~~ DONE

Extracted from CDE's `sacs2122.exe` (same approach). 5,436 SFUSD financial line items.

**Location:** `sacs-data/ua-fy2021-22/sfusd_usergl_fy2021-22.csv` + 5 reference CSVs

---

## ~~Priority 4: FY 2021-22 and FY 2022-23 Interim Reports~~ DONE

All interim reports for FY 2021-22 and FY 2022-23 have been downloaded, including COE letters.

One COE letter failed (FY 2021-22 2nd Interim — Google Drive permission restricted). If needed:
- Google Drive ID: `1ONO2TOFk6nNabOkD1pOHMm0JnK3h7IR6`
- Open in browser: `https://drive.google.com/file/d/1ONO2TOFk6nNabOkD1pOHMm0JnK3h7IR6/view`
- Save as: `interim-reports/sfcoe_2nd-interim-letter_fy2021-22.pdf`

---

## Lower Priority: Nice to Have

### QTEA & FWEA Parcel Tax Audit — FY 2022-23
The SFUSD archives page lists QTEA compliance audits for FY 19-20 through 21-22 (which we now have), but also mentions FY 22-23. We didn't find a separate link for it — it may be in the FY 2022-23 main audit report.

### ~~Scribd UTLA 2019 Tentative Agreement~~ DONE
Downloaded the official UTLA-hosted PDF (better than Scribd) from `https://utla.net/app/uploads/2022/08/UTLA-LAUSD-2019-2022-Tentative-AgreementFINALV4012219.pdf`
**Location:** `comparable-contracts/utla_lausd-tentative-agreement_2019-2022.pdf`

### ~~FY 2021-22 Budget Book Volume I~~ DONE
Downloaded both the 1st Reading (920 KB) and final version (22 MB) from Google Drive.
**Location:** `budgets/fy2021-22/sfusd_budget-book-vol-i-lcap_fy2021-22.pdf` and `sfusd_budget-book-vol-i-lcap-1st-reading_fy2021-22.pdf`

### ~~PEEF Annual Report — FY 2021-22~~ DONE
Downloaded from Google Drive via gdown.
**Location:** `parcel-tax/sfusd_peef-annual-report_fy2021-22.pdf` (3.1 MB)

### PEEF Annual Report — FY 2024-25
- Still missing. Check: `https://www.sfusd.edu/information-community/public-education-enrichment-fund-peef/peef-archive`

### Cornell Roosevelt Institute Housing/Educator Costs Report
- Was at: `https://www.cornellrooseveltinstitute.org/edu/pricedout-the-effects-of-the-housing-market-on-educators-in-san-francisco`
- Page returns 404 — removed from their site
- Try the Wayback Machine: `https://web.archive.org/web/*/https://www.cornellrooseveltinstitute.org/edu/pricedout*`

---

## Partially Resolved — Public Data Now Available

Several items previously thought to require CPRA requests are now partially available:

- **Health benefit costs**: SFHSS publishes detailed premium rate cards for SFUSD employees by plan and tier. Downloaded for 2024, 2025, and 2026 → `comparable-data/sfhss_sfusd-health-plan-rates_*.pdf`. Still need per-employee employer contribution by bargaining unit for full analysis.
- **Admin FTE data**: CDE DataQuest staff data downloaded for FY 2021-22 through 2024-25 → `comparable-data/cde_dataquest-staff-data-sfusd_*.txt`. BLA's central admin staffing audit also available → `spending-analysis/bla_sfusd-central-admin-staffing_2023-01.pdf`. UESF "Restructure it Right" report provides detailed admin position analysis → `union-resources/uesf_restructure-it-right-report_2024-02.pdf`.
- **Vendor payment data**: Board Report of Checks (July-December 2025) downloaded → `spending-analysis/warrants/`. VendorName-Amount summary also available. However, FY 2021-2024 warrant data was NOT published publicly.

## Requests Sent — Awaiting Response

### Email 1: Combined CPRA Request (sent 2026-02-08)

Sent to `publicrecords@sfusd.edu`. Combined request under the California Public Records Act (Gov. Code 7920 et seq.) covering:

1. **Accounts payable warrant registers** (Board Report of Checks) for FY 2020-21 through 2023-24 — vendor name, check/warrant number, amount, date, account code
2. **Consultant/contractor payments >$10K** (FY 2021-2026) — vendor name, contract and payment amounts, description of services, department/program, contract dates
3. **Administrative FTE breakdown by year** (FY 2020-21 through 2025-26) — central office vs. school-site admin vs. certificated vs. classified
4. **Health benefit cost detail** (FY 2021-2026) — per-employee employer/employee contribution by plan tier and bargaining unit
5. **Multi-year budget projections** — documents and scenario analyses used to inform labor negotiation positions (Jan 2024-present)

SFUSD has 10 days to respond under CPRA. *Note: Mediation session summaries were intentionally omitted to avoid slowing down the response.*

### Email 2: Education Code 42643 Warrant Register Inspection (sent 2026-02-08)

Sent to `publicrecords@sfusd.edu`. Separate request under **Education Code Section 42643**, which requires:

> *"The superintendent of schools of each county shall keep, open to the inspection of the public, a register of warrants, showing the fund upon which the requisitions have been drawn, the number, in whose favor, and for what purpose they were drawn."*

This is a **stronger legal basis than CPRA** because:
- It's a standing statutory obligation, not a records request to process
- The register must be "open to the inspection of the public" at all times
- No 10-day response window — it should be available immediately
- No exemptions or privileges apply to the register itself

The request cited SFUSD's May 2024 negative fiscal certification as undermining any claim to alternative procedures under Ed Code 42650. In SF's unique city-county structure, the SFUSD Superintendent serves as county superintendent and is the custodian of this register.

Requested FY 2020-21 through 2023-24, in electronic format (PDF/Excel/CSV).

### Why Two Separate Requests

The Ed Code 42643 angle was discovered via deep research into California education finance law. It's legally distinct from CPRA:
- **CPRA** = "give me copies of records you have" (allows 10-day response, exemptions, redactions)
- **Ed Code 42643** = "let me inspect a register you're required to maintain" (immediate access, no exemptions)

If SFUSD tries to stonewall the CPRA, the Ed Code request provides a separate enforcement path.

### Deep Research Results: Why These Records Aren't Online

Exhaustive search (2026-02-08) confirmed FY 2021-2024 warrant data exists **nowhere** online:

| Source Searched | Result |
|---|---|
| SFUSD BoardDocs (all meeting years) | Warrant PDFs only attached starting FY 2025-2026 |
| data.sfgov.org / OpenBook SF | SFUSD is separate entity, not included |
| CA State Controller (bythenumbers.sco.ca.gov) | Covers cities/counties/special districts, NOT K-12 |
| CDE / Ed-Data / SACS Data | Aggregate expenditures only, no vendor names |
| Transparent California / PublicPay / OpenTheBooks | Salary/compensation only |
| MuckRock | No financial CPRA requests filed with SFUSD |
| DocumentCloud | Nothing |
| SF Treasurer annual reports | No SFUSD warrant detail |
| Wayback Machine | No historical warrant pages on sfusd.edu |
| Google dorking (multiple queries) | No results |
| Exa deep search (multiple queries) | No results |
| OpenGov / ClearGov portals | SFUSD doesn't use any (unlike some other CA districts) |
| SF Chronicle 2023 contracts investigation | Used City/County data from data.sfgov.org, not SFUSD |
| Government Navigator | Only RFP/bid documents |

Other CA school districts (Redwood City Elementary, Newark USD) DO publish monthly warrant registers on BoardDocs. SFUSD simply chose not to until FY 2025-2026.

---

## Still Not Publicly Available — Items in CPRA Request

See `cpra_request_template.md` for pre-written request language.

1. **Consultant/contractor payments >$10K** (FY 2021-2026) — *Note: SACS Object 5800 data provides district-level consulting totals, and BoardDocs consent calendar has individual contract approvals >~$114,500, but line-item detail requires CPRA.*
2. **Administrative FTE breakdown by year** — *Note: Partially available via CDE DataQuest and BLA reports (see "Partially Resolved" above), but SFUSD's internal detailed breakdowns would be more complete.*
3. **Health benefit cost detail** — *Note: SFHSS rate cards show plan costs but not the employer contribution split.*
4. **Internal budget projections** — multi-year assumptions used in negotiations
5. **Mediation session summaries** — proposals exchanged during UESF mediation (Oct 2025-present). *Not included in the email sent — can be requested separately if needed.*
6. **Accounts Payable Warrants FY 2021-2024** — Board Report of Checks for July 2020 through June 2024. **Requested via both CPRA and Ed Code 42643.**

---

## Summary

| Item | Priority | Effort | Method |
|------|----------|--------|--------|
| ~~FY 2021-22 Annual Audit~~ | ~~High~~ | ~~Done~~ | ~~Found on BoardDocs March 2024 meeting~~ |
| ~~FY 2020-21 Unaudited Actuals SACS~~ | ~~High~~ | ~~Done~~ | ~~Extracted from CDE .exe~~ |
| ~~FY 2021-22 Unaudited Actuals SACS~~ | ~~High~~ | ~~Done~~ | ~~Extracted from CDE .exe~~ |
| ~~FY 2021-22 & 2022-23 Interim Reports~~ | ~~Medium~~ | ~~Done~~ | ~~Downloaded from Google Drive~~ |
| ~~FY 2021-22 Budget Book Volume I~~ | ~~Low~~ | ~~Done~~ | ~~Downloaded from Google Drive~~ |
| ~~PEEF FY 2021-22~~ | ~~Low~~ | ~~Done~~ | ~~Downloaded from Google Drive~~ |
| ~~Scribd UTLA 2019~~ | ~~Low~~ | ~~Done~~ | ~~Downloaded from utla.net (2019-2022 TA)~~ |
| CPRA + Ed Code 42643 requests | Medium | **Sent 2026-02-08** | Email to publicrecords@sfusd.edu — 2 emails sent |
| PEEF FY 2024-25 | Low | Low | SFUSD PEEF archive page |

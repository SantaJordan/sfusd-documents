#!/usr/bin/env python3
"""
SFUSD Document Downloader
=========================
Downloads, organizes, and indexes all SFUSD-related documents for union
negotiation analysis. Handles direct PDFs, Google Drive files, and web pages.

Usage:
    python3 download_all.py
"""

import csv
import hashlib
import io
import logging
import os
import re
import shutil
import sys
import time
import zipfile
from datetime import datetime
from pathlib import Path
from urllib.parse import unquote, urlparse

import requests
from bs4 import BeautifulSoup

try:
    import gdown
    HAS_GDOWN = True
except ImportError:
    HAS_GDOWN = False
    print("WARNING: gdown not installed. Google Drive downloads will be skipped.")
    print("Install with: pip install gdown")

# ============================================================================
# Configuration
# ============================================================================

BASE_DIR = Path(__file__).parent.resolve()
SOURCES_DIR = BASE_DIR / "_sources"
ERRORS_LOG = BASE_DIR / "download_errors.log"

# HTTP settings
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,application/pdf,*/*;q=0.8",
}
TIMEOUT = 60
MAX_RETRIES = 3
RETRY_DELAY = 2  # seconds

# ============================================================================
# Directory Structure
# ============================================================================

DIRECTORIES = [
    "budgets/fy2021-22",
    "budgets/fy2022-23",
    "budgets/fy2023-24",
    "budgets/fy2024-25",
    "budgets/fy2025-26",
    "interim-reports",
    "unaudited-actuals",
    "audits",
    "lcap",
    "fiscal-oversight",
    "bond-program",
    "parcel-tax",
    "salary-schedules",
    "labor-agreements",
    "negotiations",
    "board-presentations",
    "spending-analysis",
    "enrollment-data",
    "legal/perb-decisions",
    "legal/court-cases",
    "legal/statutes",
    "comparable-contracts",
    "comparable-data",
    "news-coverage",
    "union-resources",
]

# ============================================================================
# Existing PDFs from zip bundle — map original filename to (target_folder, new_filename)
# ============================================================================

EXISTING_PDF_MAP = {
    "SFUSD_FY2025-26_District_SACS_2nd_Reading_2025-06-24.pdf": (
        "budgets/fy2025-26",
        "sfusd_adopted-budget-sacs-2nd-reading_fy2025-26.pdf",
    ),
    "SFUSD_FY2024-25_Budget_Adoption_SACS_2024-06-25.pdf": (
        "budgets/fy2024-25",
        "sfusd_adopted-budget-sacs-2nd-reading_fy2024-25.pdf",
    ),
    "SFUSD_Recommended_Budget_Book_1st_Reading_FY2024-25_2024-06-11.pdf": (
        "budgets/fy2024-25",
        "sfusd_recommended-budget-book-1st-reading_fy2024-25.pdf",
    ),
    "SFCOE_SFUSD_LCFF_Budget_Overview_for_Parents_2024-25.pdf": (
        "lcap",
        "sfcoe_lcff-budget-overview-for-parents_fy2024-25.pdf",
    ),
    "SFUSD_Recommended_Budget_1st_Reading_FY2023-24_2023-06-06.pdf": (
        "budgets/fy2023-24",
        "sfusd_recommended-budget-1st-reading_fy2023-24.pdf",
    ),
    "SFUSD_Budget_Resolution_1st_Reading_FY2023-24_2023-06-06.pdf": (
        "budgets/fy2023-24",
        "sfusd_budget-resolution-1st-reading_fy2023-24.pdf",
    ),
    "SFUSD_Budget_Resolution_2nd_Reading_FY2023-24_2023-06-20.pdf": (
        "budgets/fy2023-24",
        "sfusd_budget-resolution-2nd-reading_fy2023-24.pdf",
    ),
    "SFUSD_Budget_Presentation_FY2022-23_2022-06-22.pdf": (
        "board-presentations",
        "sfusd_budget-presentation_fy2022-23.pdf",
    ),
    "SFUSD_Budget_Update_Presentation_FY2022-23_2022-04-06.pdf": (
        "board-presentations",
        "sfusd_budget-update-presentation_fy2022-23.pdf",
    ),
    "SFUSD_Budget_Book_Volume_II_1st_Reading_FY2021-22_2021-06-08.pdf": (
        "budgets/fy2021-22",
        "sfusd_budget-book-vol-ii-1st-reading_fy2021-22.pdf",
    ),
    "SFUSD_First_Interim_Report_FY2023-24_2023-12-12.pdf": (
        "interim-reports",
        "sfusd_1st-interim-report_fy2023-24.pdf",
    ),
    "SFUSD_Second_Interim_Report_FY2023-24_2024-03-12.pdf": (
        "interim-reports",
        "sfusd_2nd-interim-report_fy2023-24.pdf",
    ),
    "SFUSD_Third_Interim_Financial_Report_FY2024-25_2025-05-13.pdf": (
        "interim-reports",
        "sfusd_3rd-interim-report_fy2024-25.pdf",
    ),
    "SFUSD_Budget_Updates_and_First_Interim_Presentation_2024-12-10.pdf": (
        "interim-reports",
        "sfusd_1st-interim-presentation_fy2024-25.pdf",
    ),
    "SFUSD_Audit_Report_FY2023-24_YearEnded_2024-06-30.pdf": (
        "audits",
        "sfusd_annual-audit_fy2023-24.pdf",
    ),
    "SFUSD_Audit_Report_FY2022-23_YearEnded_2023-06-30.pdf": (
        "audits",
        "sfusd_annual-audit_fy2022-23.pdf",
    ),
    "FCMAT_SFUSD_Fiscal_Health_Risk_Analysis_2022-03-03.pdf": (
        "fiscal-oversight",
        "fcmat_fiscal-health-risk-analysis_2022-03.pdf",
    ),
    "SFUSD_Fiscal_Stabilization_Plan_Update_2024-06.pdf": (
        "fiscal-oversight",
        "sfusd_fiscal-stabilization-plan_2024-06.pdf",
    ),
    "SFUSD_Fiscal_Stabilization_Plan_Update_2024-12.pdf": (
        "fiscal-oversight",
        "sfusd_fiscal-stabilization-plan_2024-12.pdf",
    ),
    "SFUSD_Fiscal_Stabilization_Plan_Update_2025-03-17.pdf": (
        "fiscal-oversight",
        "sfusd_fiscal-stabilization-plan_2025-03.pdf",
    ),
}

# ============================================================================
# Download Manifest — All documents to download
# ============================================================================
# Each entry: (url, target_folder, filename, description, download_type)
# download_type: "pdf", "web_text", "gdrive"

DOWNLOADS = [
    # ── Budgets ──────────────────────────────────────────────────────────
    (
        "https://go.boarddocs.com/ca/sfusd/Board.nsf/files/D6G3WA08D0A1/$file/FY%2024-25%20SFUSD%20Budget%20Adoption_2nd%20Reading%20SACS%20Forms%2006-25-2024.pdf",
        "budgets/fy2024-25",
        "sfusd_adopted-budget-sacs-2nd-reading_fy2024-25.pdf",
        "FY 2024-25 Adopted Budget SACS (2nd Reading)",
        "pdf",
    ),
    (
        "https://go.boarddocs.com/ca/sfusd/Board.nsf/files/DHU32S04CBAE/$file/2025-26%20District%20SACS%20%282nd%20Reading%29.pdf",
        "budgets/fy2025-26",
        "sfusd_adopted-budget-sacs-2nd-reading_fy2025-26.pdf",
        "FY 2025-26 Adopted Budget SACS (2nd Reading)",
        "pdf",
    ),
    (
        "https://go.boarddocs.com/ca/sfusd/Board.nsf/files/CSEMQR5C5A01/$file/2023-24%20Recommended%20Budget%20%281st%20Reading%29%20%281%29.pdf",
        "budgets/fy2023-24",
        "sfusd_recommended-budget-1st-reading_fy2023-24.pdf",
        "FY 2023-24 Recommended Budget (1st Reading)",
        "pdf",
    ),
    (
        "https://go.boarddocs.com/ca/sfusd/Board.nsf/files/CDCUEZ7F79D4/$file/Proposed%20FY%202022-23%20and%20FY%202023-24%20Budget%20Balancing%20Plan.pdf",
        "budgets/fy2022-23",
        "sfusd_budget-balancing-plan_fy2022-23_fy2023-24.pdf",
        "FY 2022-23/2023-24 Budget Balancing Plan",
        "pdf",
    ),
    (
        "https://go.boarddocs.com/ca/sfusd/Board.nsf/files/CFM2ZQ04A372/$file/22%20-%2006.22%20Special%20Meeting_Budget%20Presentation.pdf",
        "board-presentations",
        "sfusd_budget-presentation_fy2022-23.pdf",
        "FY 2022-23 Budget Presentation (Special Meeting)",
        "pdf",
    ),
    (
        "https://go.boarddocs.com/ca/sfusd/Board.nsf/files/CD7T2Y73B70F/$file/22%20-%2004.06%20FY%202022-23%20Budget%20Update_PRESENTATION%20%28final%29.pdf",
        "board-presentations",
        "sfusd_budget-update-presentation_fy2022-23.pdf",
        "FY 2022-23 Budget Update Presentation (Apr 2022)",
        "pdf",
    ),
    (
        "https://go.boarddocs.com/ca/sfusd/Board.nsf/files/CD7T3173E68F/$file/22%20-%2004.08%20Memo%20re.%20Budget%20Scenario%20Planning%20for%20School%20Sites.pdf",
        "board-presentations",
        "sfusd_budget-scenario-planning-memo_2022-04.pdf",
        "Budget Scenario Planning Memo (Apr 2022)",
        "pdf",
    ),

    # ── Interim Reports ──────────────────────────────────────────────────
    (
        "https://go.boarddocs.com/ca/sfusd/Board.nsf/files/DBQTWW796A69/$file/%5BUpdated%2012_7_24-v2%5D-SFUSD%20Budget%20Updates%20and%202024-25%20First%20Interim-12.10.24.pptx%20%281%29.pdf",
        "interim-reports",
        "sfusd_1st-interim-presentation_fy2024-25.pdf",
        "FY 2024-25 1st Interim Presentation (Updated Dec 2024)",
        "pdf",
    ),
    (
        "https://go.boarddocs.com/ca/sfusd/Board.nsf/files/DBQTX37985CE/$file/%5BUpdated-12.10.24-final%5DSFUSD-1st_Interim-24-25.pdf",
        "interim-reports",
        "sfusd_1st-interim-report_fy2024-25.pdf",
        "FY 2024-25 1st Interim Report",
        "pdf",
    ),
    (
        "https://go.boarddocs.com/ca/sfusd/Board.nsf/files/DFRQZ206A7C2/$file/SFUSD%202nd%20Interim%20Financial%20Report.pdf",
        "interim-reports",
        "sfusd_2nd-interim-report_fy2024-25.pdf",
        "FY 2024-25 2nd Interim Report",
        "pdf",
    ),
    (
        "https://go.boarddocs.com/ca/sfusd/Board.nsf/files/CYF2SZ03A73C/$file/SFUSD_2023-2024%201st%20Interim%20Report%2020231212-Updated.pdf",
        "interim-reports",
        "sfusd_1st-interim-report_fy2023-24.pdf",
        "FY 2023-24 1st Interim Report",
        "pdf",
    ),
    (
        "https://go.boarddocs.com/ca/sfusd/Board.nsf/files/D4W3D50141F3/$file/2024-0201a%2038%20San%20Francisco%20COE%20USD%202023-24%202nd%20Interim%20FINAL.pdf",
        "interim-reports",
        "sfcoe_2nd-interim-letter_fy2023-24.pdf",
        "FY 2023-24 2nd Interim Letter (COE)",
        "pdf",
    ),
    (
        "https://go.boarddocs.com/ca/sfusd/Board.nsf/files/DJJRNA70B5A3/$file/2026-12-09%201st%20Interim%20Report%20Presentation.pdf",
        "interim-reports",
        "sfusd_1st-interim-presentation_fy2025-26.pdf",
        "FY 2025-26 1st Interim Presentation",
        "pdf",
    ),

    # ── Unaudited Actuals ────────────────────────────────────────────────
    (
        "https://go.boarddocs.com/ca/sfusd/Board.nsf/files/D8PU7L7CF28D/$file/FY%2023-24%20Unaudited%20Actuals%20-%20District.pdf",
        "unaudited-actuals",
        "sfusd_unaudited-actuals-sacs_fy2023-24.pdf",
        "FY 2023-24 Unaudited Actuals (SACS, 158pp)",
        "pdf",
    ),
    (
        "https://go.boarddocs.com/ca/sfusd/Board.nsf/files/D8PU7N7CF56F/$file/2023-24%20Unaudited%20Actuals%20Final%20PPT.pdf",
        "unaudited-actuals",
        "sfusd_unaudited-actuals-presentation_fy2023-24.pdf",
        "FY 2023-24 Unaudited Actuals Presentation",
        "pdf",
    ),
    (
        "https://go.boarddocs.com/ca/sfusd/Board.nsf/files/C6BVKF7BB2C2/$file/Resolution_FY%202020-21%20Unaudited%20Actuals_DRAFT%20for%2010.12.21%20Board%20Meeting.pdf",
        "unaudited-actuals",
        "sfusd_unaudited-actuals-resolution_fy2020-21.pdf",
        "FY 2020-21 Unaudited Actuals Resolution",
        "pdf",
    ),

    # ── Audits ───────────────────────────────────────────────────────────
    (
        "https://go.boarddocs.com/ca/sfusd/Board.nsf/files/D4W23E00326C/$file/San%20Francisco%20Unified%20School%20District%20Audit%20Report%20FY%2022-23.pdf",
        "audits",
        "sfusd_annual-audit_fy2022-23.pdf",
        "FY 2022-23 Annual Audit Report",
        "pdf",
    ),

    # ── Fiscal Oversight ─────────────────────────────────────────────────
    (
        "https://www.fcmat.org/PublicationsReports/san-francisco-usd-report-1484.pdf",
        "fiscal-oversight",
        "fcmat_special-education-review_2025-01.pdf",
        "FCMAT Special Education Review (Jan 2025)",
        "pdf",
    ),
    (
        "https://go.boarddocs.com/ca/sfusd/Board.nsf/files/CDCUEY7F6A01/$file/San%20Francisco%20USD%20FHRA%20final%20report%20%281%29.pdf",
        "fiscal-oversight",
        "fcmat_fiscal-health-risk-analysis_2022-03.pdf",
        "FCMAT Fiscal Health Risk Assessment",
        "pdf",
    ),
    (
        "https://go.boarddocs.com/ca/sfusd/Board.nsf/files/DBQTY57997AA/$file/SFUSD%20Fiscal%20Stabilization%20Plan%20Update%20as%20of%20December%202024.docx.pdf",
        "fiscal-oversight",
        "sfusd_fiscal-stabilization-plan_2024-12.pdf",
        "Fiscal Stabilization Plan Update (Dec 2024)",
        "pdf",
    ),
    (
        "https://go.boarddocs.com/ca/sfusd/Board.nsf/files/DEK3SM08482F/$file/G3_SFUSD%20Fiscal%20Stabilization%20Plan%20Update%20%281%29%20.docx.pdf",
        "fiscal-oversight",
        "sfusd_fiscal-stabilization-plan_2025-03.pdf",
        "Fiscal Stabilization Plan Update (Mar 2025)",
        "pdf",
    ),

    # ── Spending Analysis ────────────────────────────────────────────────
    (
        "https://sfbos.org/sites/default/files/BLA.SFUSD_.Budget%20Analysis.061323.pdf",
        "spending-analysis",
        "bla_sfusd-expenditure-analysis_2023-06.pdf",
        "BLA SFUSD Expenditure Analysis (Jun 2023)",
        "pdf",
    ),

    # ── PERB Decisions ───────────────────────────────────────────────────
    (
        "https://perb.ca.gov/wp-content/uploads/decisionbank/decision-0206E.pdf",
        "legal/perb-decisions",
        "perb_decision-0206e-moreno-valley_1982.pdf",
        "PERB Decision 0206E (Moreno Valley)",
        "pdf",
    ),
    (
        "https://perb.ca.gov/wp-content/uploads/decisionbank/decision-2906e.pdf",
        "legal/perb-decisions",
        "perb_decision-2906e-oakland-usd_2024.pdf",
        "PERB Decision 2906E (Oakland USD, 2024)",
        "pdf",
    ),
    (
        "https://perb.ca.gov/wp-content/uploads/decisionbank/decision-2475E.pdf",
        "legal/perb-decisions",
        "perb_decision-2475e-raines-v-utla_2016.pdf",
        "PERB Decision 2475E (Raines v. UTLA)",
        "pdf",
    ),
    (
        "https://perb.ca.gov/wp-content/uploads/decisionbank/decision-2803e.pdf",
        "legal/perb-decisions",
        "perb_decision-2803e-oxnard_2022.pdf",
        "PERB Decision 2803E (Oxnard)",
        "pdf",
    ),
    (
        "https://perb.ca.gov/wp-content/uploads/decisionbank/decision-0279E.pdf",
        "legal/perb-decisions",
        "perb_decision-0279e-rio-hondo_1983.pdf",
        "PERB Decision 0279E (Rio Hondo)",
        "pdf",
    ),

    # ── Comparable Contracts ─────────────────────────────────────────────
    (
        "https://www.cps.edu/globalassets/cps-pages/about-cps/policies/administrative-hearings/ctu-contract-2019-24-2021-06-17-indd.pdf",
        "comparable-contracts",
        "ctu_cba-2019-2024_chicago.pdf",
        "CTU 2019-24 Contract (Chicago)",
        "pdf",
    ),
    (
        "https://www.berkeleyschools.net/wp-content/uploads/2024/03/BFT-CBA-20222025-VER2.pdf",
        "comparable-contracts",
        "bft_cba-2022-2025_berkeley.pdf",
        "Berkeley Federation of Teachers CBA 2022-2025",
        "pdf",
    ),
    (
        "https://uesf.org/wp-content/uploads/2018/04/Certificated-Collective-Bargaining-Agreement-7-1-17-thru-6-30-20-pre-final.pdf",
        "comparable-contracts",
        "uesf_cba-2017-2020_sfusd.pdf",
        "UESF Previous CBA 2017-2020",
        "pdf",
    ),

    # ── Union Resources ──────────────────────────────────────────────────
    (
        "https://uesf.org/wp-content/uploads/2021/03/UESF-Constitution-and-Bylaws-2017-updated.pdf",
        "union-resources",
        "uesf_constitution-and-bylaws_2017.pdf",
        "UESF Constitution & Bylaws",
        "pdf",
    ),
    (
        "https://www.seiu1021.org/sites/main/files/file-attachments/sfusd_strike_faqs_final2.pdf",
        "union-resources",
        "seiu1021_sfusd-strike-faq_2026.pdf",
        "SEIU 1021 Strike FAQ",
        "pdf",
    ),

    # ── LCAP ─────────────────────────────────────────────────────────────
    (
        "https://api.mycdeconnect.org/reports/lcap/25-26?id=5042aa77-c301-4c61-a2ae-69f1ef95bac3",
        "lcap",
        "cde_lcap-annual-update_fy2025-26.pdf",
        "2025-26 LCAP Annual Update (CDE)",
        "pdf",
    ),
    (
        "https://cdeunifiedstoragewest.blob.core.windows.net/lcaps/ba55455a-e060-450b-93ca-c0f87925b54b.pdf",
        "lcap",
        "sfcoe_lcff-budget-overview-for-parents_fy2024-25.pdf",
        "2024-25 LCAP Budget Overview (CDE)",
        "pdf",
    ),

    # ── Court Cases (save as text) ───────────────────────────────────────
    (
        "https://law.justia.com/cases/california/supreme-court/3d/38/564.html",
        "legal/court-cases",
        "justia_county-sanitation-v-la-county-employees_1985.txt",
        "County Sanitation v. LA County Employees (1985)",
        "web_text",
    ),
    (
        "https://law.justia.com/cases/california/court-of-appeal/2025/a171007.html",
        "legal/court-cases",
        "justia_perb-2906e-court-of-appeal_2025.txt",
        "Court of Appeal - PERB 2906E affirmation (2025)",
        "web_text",
    ),
    (
        "https://law.justia.com/cases/california/court-of-appeal/3d/142/191.html",
        "legal/court-cases",
        "justia_moreno-valley-court-of-appeal_1986.txt",
        "Moreno Valley Court of Appeal",
        "web_text",
    ),

    # ── California Statutes (save as text) ───────────────────────────────
    (
        "https://leginfo.legislature.ca.gov/faces/codes_displaySection.xhtml?sectionNum=3540.&lawCode=GOV",
        "legal/statutes",
        "ca-gov-code_eera-section-3540_current.txt",
        "EERA (Gov Code 3540)",
        "web_text",
    ),
    (
        "https://leginfo.legislature.ca.gov/faces/codes_displaySection.xhtml?lawCode=GOV&sectionNum=3543.2.",
        "legal/statutes",
        "ca-gov-code_scope-of-bargaining-3543-2_current.txt",
        "Gov Code 3543.2 (Scope of Bargaining)",
        "web_text",
    ),
    (
        "https://leginfo.legislature.ca.gov/faces/codes_displaySection.xhtml?sectionNum=3548.&lawCode=GOV",
        "legal/statutes",
        "ca-gov-code_impasse-3548_current.txt",
        "Gov Code 3548 (Impasse Procedures)",
        "web_text",
    ),
    (
        "https://leginfo.legislature.ca.gov/faces/codes_displaySection.xhtml?lawCode=EDC&sectionNum=41376",
        "legal/statutes",
        "ca-ed-code_class-size-41376_current.txt",
        "Ed Code 41376 (Class Size)",
        "web_text",
    ),
    (
        "https://leginfo.legislature.ca.gov/faces/billNavClient.xhtml?bill_id=202520260AB560",
        "legal/statutes",
        "ca-ab560_sped-caseload_2025.txt",
        "AB 560 (Special Education Caseload)",
        "web_text",
    ),
    (
        "https://leginfo.legislature.ca.gov/faces/codes_displayText.xhtml?lawCode=CONS&article=IX",
        "legal/statutes",
        "ca-constitution_article-ix-education_current.txt",
        "CA Constitution Article IX (Education)",
        "web_text",
    ),

    # ── Comparable Data (save as text) ───────────────────────────────────
    (
        "https://www.bls.gov/regions/west/news-release/consumerpriceindex_sanfrancisco.htm",
        "comparable-data",
        "bls_sf-cpi-data_current.txt",
        "BLS SF CPI Data",
        "web_text",
    ),
    (
        "https://www.census.gov/quickfacts/sanfranciscocitycalifornia",
        "comparable-data",
        "census_quickfacts-sf_current.txt",
        "Census QuickFacts San Francisco",
        "web_text",
    ),
    (
        "https://transparentcalifornia.com/salaries/school-districts/san-francisco/san-francisco-unified/",
        "comparable-data",
        "transparent-ca_sfusd-salaries_current.txt",
        "Transparent California SFUSD Salaries",
        "web_text",
    ),
    (
        "https://www.ed-data.org/district/San-Francisco/San-Francisco-Unified",
        "comparable-data",
        "ed-data_sfusd-financial-profile_current.txt",
        "Ed-Data SFUSD Financial Profile",
        "web_text",
    ),
    (
        "https://nces.ed.gov/ccd/districtsearch/district_detail.asp?ID2=0634410",
        "comparable-data",
        "nces_sfusd-district-detail_current.txt",
        "NCES District Detail - SFUSD",
        "web_text",
    ),

    # ── Union Resources (web text) ───────────────────────────────────────
    (
        "https://www.bargainingforthecommongood.org/",
        "union-resources",
        "bcg_bargaining-common-good-framework_current.txt",
        "Bargaining for the Common Good Framework",
        "web_text",
    ),

    # ── News Coverage (save as text) ─────────────────────────────────────
    (
        "https://www.sfchronicle.com/sf/article/sfusd-schools-teachers-union-strike-21339398.php",
        "news-coverage",
        "sf-chronicle_strike-overview_2026-02.txt",
        "SF Chronicle - Strike overview",
        "web_text",
    ),
    (
        "https://www.sfchronicle.com/sf/article/teachers-brink-strike-fact-finding-report-district-21333435.php",
        "news-coverage",
        "sf-chronicle_fact-finding-analysis_2026-02.txt",
        "SF Chronicle - Fact-finding analysis",
        "web_text",
    ),
    (
        "https://projects.sfchronicle.com/2016/teacher-pay/",
        "news-coverage",
        "sf-chronicle_teacher-pay-crisis-investigation_2016.txt",
        "SF Chronicle - Teacher pay crisis (2016 investigation)",
        "web_text",
    ),
    (
        "https://www.sfchronicle.com/bayarea/article/audit-of-s-f-school-district-finances-raises-as-17709223.php",
        "news-coverage",
        "sf-chronicle_admin-spending-audit_2023-01.txt",
        "SF Chronicle - Admin spending audit",
        "web_text",
    ),
    (
        "https://www.sfchronicle.com/bayarea/article/sfusd-teacher-salaries-raises-18331238.php",
        "news-coverage",
        "sf-chronicle_teacher-salary-comparison_2023.txt",
        "SF Chronicle - Teacher salary comparison",
        "web_text",
    ),
    (
        "https://missionlocal.org/2025/12/sfusd-teacher-union-strike-vote-walkout/",
        "news-coverage",
        "mission-local_strike-vote-99-percent_2025-12.txt",
        "Mission Local - Strike vote (99.34%)",
        "web_text",
    ),
    (
        "https://missionlocal.org/2026/02/school-principals-maintenance-workers-if-teachers-strike-we-will-too/",
        "news-coverage",
        "mission-local_sympathy-strikes-uas-seiu_2026-02.txt",
        "Mission Local - Sympathy strikes (UAS + SEIU)",
        "web_text",
    ),
    (
        "https://missionlocal.org/2026/02/teachers-others-shocked-to-get-sfusd-assignments-for-strike-day/",
        "news-coverage",
        "mission-local_strike-day-assignments-shock_2026-02.txt",
        "Mission Local - Strike day assignments shock",
        "web_text",
    ),
    (
        "https://missionlocal.org/2023/08/sfusd-prepares-for-new-academic-year-amid-teacher-shortages/",
        "news-coverage",
        "mission-local_teacher-shortages_2023-08.txt",
        "Mission Local - Teacher shortages (2023)",
        "web_text",
    ),
    (
        "https://sfstandard.com/2026/02/05/sfusd-teachers-strike-starts-february-9/",
        "news-coverage",
        "sf-standard_strike-date-announcement_2026-02-05.txt",
        "SF Standard - Strike date announcement",
        "web_text",
    ),
    (
        "https://sfstandard.com/2026/02/06/sfusd-strike-update-what-to-know/",
        "news-coverage",
        "sf-standard_what-to-know_2026-02-06.txt",
        "SF Standard - What to know",
        "web_text",
    ),
    (
        "https://sfstandard.com/2026/02/05/parents-react-sfusd-teachers-strike/",
        "news-coverage",
        "sf-standard_parent-reactions_2026-02-05.txt",
        "SF Standard - Parent reactions",
        "web_text",
    ),
    (
        "https://sfstandard.com/2026/02/07/sfusd-teachers-strike-negotiations-weekend/",
        "news-coverage",
        "sf-standard_last-ditch-negotiations_2026-02-07.txt",
        "SF Standard - Last-ditch negotiations",
        "web_text",
    ),
    (
        "https://sfstandard.com/2026/02/03/will-50-000-kids-go-teachers-strike-sfusd-union-offer-half-baked-plans/",
        "news-coverage",
        "sf-standard_where-will-50k-kids-go_2026-02-03.txt",
        "SF Standard - Where will 50K kids go?",
        "web_text",
    ),
    (
        "https://sfstandard.com/2023/01/10/san-francisco-schools-sfusd-spending-central-administration-audit/",
        "news-coverage",
        "sf-standard_admin-spending-report_2023-01.txt",
        "SF Standard - Admin spending report",
        "web_text",
    ),
    (
        "https://sfstandard.com/2026/01/27/need-know-looming-teachers-strike/",
        "news-coverage",
        "sf-standard_need-to-know-about-strike_2026-01.txt",
        "SF Standard - Need to know about strike",
        "web_text",
    ),
    (
        "https://www.kqed.org/news/12072392/san-francisco-teachers-will-call-for-a-strike-next-week",
        "news-coverage",
        "kqed_strike-announcement-vacancies_2026-02.txt",
        "KQED - Strike announcement & vacancies",
        "web_text",
    ),
    (
        "https://www.kqed.org/news/12072028/2026-san-francisco-teachers-strike-sfusd-when-sf-union-childcare-after-school-programs-meals",
        "news-coverage",
        "kqed_families-what-to-know_2026-02.txt",
        "KQED - Families: what to know",
        "web_text",
    ),
    (
        "https://www.kqed.org/news/12072350/san-francisco-teachers-are-on-the-brink-of-a-strike-after-mediation-ends-with-no-deal",
        "news-coverage",
        "kqed_mediation-failure_2026-02.txt",
        "KQED - Mediation failure",
        "web_text",
    ),
    (
        "https://www.kqed.org/news/12066097/sfusd-teachers-overwhelmingly-vote-to-authorize-the-first-strike-in-49-years",
        "news-coverage",
        "kqed_authorization-vote_2025-12.txt",
        "KQED - Authorization vote (99.3%)",
        "web_text",
    ),
    (
        "https://www.kqed.org/news/12072599/sf-schools-will-close-if-teachers-strike-heres-how-city-hall-plans-to-step-in",
        "news-coverage",
        "kqed_schools-close-city-hall-steps-in_2026-02.txt",
        "KQED - Schools will close, City Hall steps in",
        "web_text",
    ),
    (
        "https://growsf.org/news/2026-02-06-sfusd-strike-looms/",
        "news-coverage",
        "growsf_strike-cost-analysis_2026-02.txt",
        "GrowSF - Strike cost analysis ($7-10M/day)",
        "web_text",
    ),
    (
        "https://48hills.org/2024/02/sfusds-administrative-bloat-questioned-ahead-of-expected-cuts-layoff-notices/",
        "news-coverage",
        "48hills_admin-bloat-analysis_2024-02.txt",
        "48 Hills - Admin bloat analysis",
        "web_text",
    ),
    (
        "https://edsource.org/updates/los-angeles-san-francisco-teachers-unions-vote-to-authorize-a-strike",
        "news-coverage",
        "edsource_strike-authorization_2025-12.txt",
        "EdSource - Strike authorization",
        "web_text",
    ),
    (
        "https://edsource.org/2019/tentative-agreement-reached-in-oakland-unified-teachers-strike/609342",
        "news-coverage",
        "edsource_oea-2019-settlement_2019.txt",
        "EdSource - OEA 2019 settlement",
        "web_text",
    ),
    (
        "https://edsource.org/updates/school-districts-with-stalled-teacher-contract-negotiations-grows",
        "news-coverage",
        "edsource_stalled-negotiations-tracker_2025.txt",
        "EdSource - Stalled negotiations tracker",
        "web_text",
    ),
    (
        "https://www.chalkbeat.org/chicago/2025/02/06/ctu-rejects-fact-finder-report-in-ongoing-contract-talks-with-cps/",
        "news-coverage",
        "chalkbeat_ctu-fact-finding-rejection_2025-02.txt",
        "Chalkbeat - CTU fact-finding rejection",
        "web_text",
    ),
    (
        "https://www.cornellrooseveltinstitute.org/edu/pricedout-the-effects-of-the-housing-market-on-educators-in-san-francisco",
        "news-coverage",
        "cornell-roosevelt_housing-educator-costs-sf_2024.txt",
        "Cornell Roosevelt Institute - Housing/educator costs",
        "web_text",
    ),
    (
        "https://labornotes.org/2023/08/big-bargaining-oakland-led-big-gains",
        "news-coverage",
        "labor-notes_oakland-bargaining-gains_2023-08.txt",
        "Labor Notes - Oakland bargaining gains",
        "web_text",
    ),
    (
        "https://www.ppssf.org/news/2025/3/8/summaryofaudit",
        "news-coverage",
        "ppssf_fy2023-24-audit-summary_2025-03.txt",
        "PPSSF - FY 2023-24 audit summary",
        "web_text",
    ),
    (
        "https://sfparents.org/updates-on-the-current-sfusd-budget-situation/",
        "news-coverage",
        "sfparents_budget-situation-analysis_2024.txt",
        "SF Parents - Budget situation analysis",
        "web_text",
    ),
    (
        "https://sfeducation.substack.com/p/sfusds-per-pupil-expenditures-try",
        "news-coverage",
        "sfeducation_per-pupil-expenditures_2024.txt",
        "SFEducation Substack - Per-pupil expenditures",
        "web_text",
    ),
    (
        "https://sfeducation.substack.com/p/salaries-staffing-and-school-sizes",
        "news-coverage",
        "sfeducation_salaries-staffing-school-sizes_2024.txt",
        "SFEducation Substack - Salaries & staffing",
        "web_text",
    ),

    # ── SFUSD Official Pages (save as text) ──────────────────────────────
    (
        "https://www.sfusd.edu/information-employees/labor-relations/negotiations-updates/status-sfusd-negotiations-uesf",
        "negotiations",
        "sfusd_negotiations-status-uesf_current.txt",
        "SFUSD Negotiations status (UESF)",
        "web_text",
    ),
    (
        "https://www.sfusd.edu/about-sfusd/sfusd-news/press-releases/2026-02-04-sfusd-labor-fact-finding-report-reaffirms-districts-commitment-fair-responsible-agreement",
        "negotiations",
        "sfusd_fact-finding-press-release_2026-02-04.txt",
        "SFUSD Fact-finding press release",
        "web_text",
    ),
    (
        "https://www.sfusd.edu/announcements/2026-02-05-feb-5-845-am-important-update-regarding-labor-negotiations-schools-open",
        "negotiations",
        "sfusd_feb5-negotiations-update_2026-02-05.txt",
        "SFUSD Feb 5 negotiations update",
        "web_text",
    ),
    (
        "https://www.sfusd.edu/about-sfusd/sfusd-news/press-releases/2024-05-03-sfusd-continues-serious-budget-corrective-actions",
        "fiscal-oversight",
        "sfusd_negative-certification-press-release_2024-05.txt",
        "SFUSD Negative certification press release",
        "web_text",
    ),
    (
        "https://www.sfusd.edu/about-sfusd/sfusd-news/press-releases/2025-06-24-sf-board-education-adopts-budget-2025-26-school-year",
        "budgets/fy2025-26",
        "sfusd_budget-adoption-press-release_fy2025-26.txt",
        "SFUSD Budget adoption 2025-26 press release",
        "web_text",
    ),
    (
        "https://www.sfusd.edu/announcements/2025-02-19-2024-2025-facts-glance",
        "enrollment-data",
        "sfusd_facts-at-a-glance_fy2024-25.txt",
        "SFUSD Facts at a Glance 2024-25",
        "web_text",
    ),
    (
        "https://careers.sfusd.edu/content/TEACHERS/?locale=en_US",
        "salary-schedules",
        "sfusd_teacher-careers-salary-info_current.txt",
        "SFUSD Careers/salary info",
        "web_text",
    ),
]

# ── Google Drive Downloads ───────────────────────────────────────────────
GDRIVE_DOWNLOADS = [
    (
        "1E48-jhGbLwNFvV3125MNAhv-x1_zAl6c",
        "negotiations",
        "perb_fact-finding-report_2026-02.pdf",
        "PERB Fact-Finding Report (Feb 2026)",
    ),
    (
        "1bPwiiEfUdK8sCt_TOsd6CvRGImK4eSVe",
        "negotiations",
        "sfusd_latest-offer_2026-02-05.pdf",
        "SFUSD Latest Offer (Feb 5, 2026)",
    ),
    (
        "119FpZ_9xwvHtD1E-NW-VspsWtlPovoRN",
        "labor-agreements",
        "uesf_certificated-cba_2023-2025.pdf",
        "UESF Certificated CBA 2023-2025",
    ),
    (
        "1vbf1QbII7ZSgM_TsS6eHBOCpMvddu646",
        "labor-agreements",
        "uesf_certificated-cba_2020-2023.pdf",
        "UESF Certificated CBA 2020-2023",
    ),
    (
        "1jQgfeasMZNAflYjS4SS7Y25ExPoC9CiX",
        "labor-agreements",
        "seiu1021_cba_2022-2025.pdf",
        "SEIU 1021 CBA 2022-2025",
    ),
]

# Scribd is hard to download programmatically — will go to manual
MANUAL_NOTES = [
    {
        "url": "https://www.scribd.com/document/398012141/UTLA-LAUSD-Tentative-Agreement-Full-Text-Jan-22-2019",
        "folder": "comparable-contracts",
        "filename": "utla_tentative-agreement_2019.pdf",
        "description": "UTLA 2019 Tentative Agreement (Scribd — requires login)",
    },
]


# ============================================================================
# Logging Setup
# ============================================================================

def setup_logging():
    """Configure logging to both console and file."""
    logger = logging.getLogger("sfusd_downloader")
    logger.setLevel(logging.INFO)

    # Console handler
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.INFO)
    ch.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(ch)

    # File handler
    fh = logging.FileHandler(ERRORS_LOG, mode="w")
    fh.setLevel(logging.WARNING)
    fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    logger.addHandler(fh)

    return logger


log = setup_logging()


# ============================================================================
# Helper Functions
# ============================================================================

def create_directories():
    """Create the full directory structure."""
    log.info("Creating directory structure...")
    for d in DIRECTORIES:
        (BASE_DIR / d).mkdir(parents=True, exist_ok=True)
    log.info(f"  Created {len(DIRECTORIES)} directories")


def unzip_and_sort_existing():
    """Extract existing PDFs from the zip bundle and sort into folders."""
    zip_path = SOURCES_DIR / "SFUSD_public_docs_bundle.zip"
    if not zip_path.exists():
        log.warning(f"Zip bundle not found at {zip_path}")
        return []

    log.info("Extracting and sorting existing PDFs from zip bundle...")
    results = []

    with zipfile.ZipFile(zip_path, "r") as zf:
        for member in zf.namelist():
            basename = os.path.basename(member)
            if basename in EXISTING_PDF_MAP:
                target_folder, new_name = EXISTING_PDF_MAP[basename]
                target_path = BASE_DIR / target_folder / new_name

                if target_path.exists():
                    log.info(f"  [SKIP] Already exists: {new_name}")
                    results.append({
                        "filename": new_name,
                        "folder": target_folder,
                        "description": f"From zip: {basename}",
                        "source": "zip_bundle",
                        "status": "exists",
                    })
                    continue

                # Extract to target
                data = zf.read(member)
                target_path.write_bytes(data)
                size_kb = len(data) / 1024
                log.info(f"  [OK] {new_name} ({size_kb:.0f} KB) -> {target_folder}/")
                results.append({
                    "filename": new_name,
                    "folder": target_folder,
                    "description": f"From zip: {basename}",
                    "source": "zip_bundle",
                    "status": "ok",
                    "size": len(data),
                })

    log.info(f"  Sorted {len(results)} existing PDFs")
    return results


def download_pdf(url, target_path, description, retries=MAX_RETRIES):
    """Download a PDF (or binary file) from a URL."""
    for attempt in range(retries):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT, stream=True, allow_redirects=True)
            resp.raise_for_status()

            content_type = resp.headers.get("content-type", "").lower()
            data = resp.content

            # Basic validation — check for HTML error pages masquerading as PDFs
            if target_path.suffix == ".pdf":
                if data[:5] != b"%PDF-" and b"<html" in data[:1000].lower():
                    log.warning(f"  [WARN] Got HTML instead of PDF for {description}")
                    return {"status": "error", "error": "Received HTML instead of PDF"}

            target_path.write_bytes(data)
            size_kb = len(data) / 1024
            return {"status": "ok", "size": len(data)}

        except requests.exceptions.RequestException as e:
            if attempt < retries - 1:
                time.sleep(RETRY_DELAY * (attempt + 1))
                continue
            return {"status": "error", "error": str(e)}

    return {"status": "error", "error": "Max retries exceeded"}


def save_web_page_as_text(url, target_path, description, retries=MAX_RETRIES):
    """Fetch a web page and save its main text content."""
    for attempt in range(retries):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT, allow_redirects=True)
            resp.raise_for_status()

            soup = BeautifulSoup(resp.text, "html.parser")

            # Remove scripts, styles, nav, footer, etc.
            for tag in soup.find_all(["script", "style", "nav", "footer", "header",
                                       "aside", "iframe", "noscript"]):
                tag.decompose()

            # Try to find main content area
            main = (
                soup.find("article")
                or soup.find("main")
                or soup.find("div", class_=re.compile(r"(content|article|post|entry)", re.I))
                or soup.find("div", id=re.compile(r"(content|article|post|entry)", re.I))
                or soup.body
                or soup
            )

            # Extract text
            text = main.get_text(separator="\n", strip=True)

            # Clean up excessive blank lines
            text = re.sub(r"\n{3,}", "\n\n", text)

            # Add header with source info
            header = f"Source: {url}\nSaved: {datetime.now().strftime('%Y-%m-%d %H:%M')}\nDescription: {description}\n{'='*80}\n\n"
            full_text = header + text

            target_path.write_text(full_text, encoding="utf-8")
            return {"status": "ok", "size": len(full_text.encode("utf-8"))}

        except requests.exceptions.RequestException as e:
            if attempt < retries - 1:
                time.sleep(RETRY_DELAY * (attempt + 1))
                continue
            return {"status": "error", "error": str(e)}

    return {"status": "error", "error": "Max retries exceeded"}


def download_from_gdrive(file_id, target_path, description):
    """Download a file from Google Drive using gdown."""
    if not HAS_GDOWN:
        return {"status": "manual", "error": "gdown not installed"}

    try:
        url = f"https://drive.google.com/uc?id={file_id}"
        output = str(target_path)
        gdown.download(url, output, quiet=True, fuzzy=True)

        if target_path.exists() and target_path.stat().st_size > 0:
            return {"status": "ok", "size": target_path.stat().st_size}
        else:
            return {"status": "manual", "error": "gdown produced empty/no file (may require login)"}
    except Exception as e:
        return {"status": "manual", "error": f"gdown error: {str(e)}"}


def run_all_downloads():
    """Execute all downloads and return results."""
    results = []

    # Direct downloads (PDFs and web pages)
    total = len(DOWNLOADS)
    log.info(f"\nDownloading {total} files (PDFs + web pages)...")

    for i, (url, folder, filename, description, dtype) in enumerate(DOWNLOADS, 1):
        target_path = BASE_DIR / folder / filename
        prefix = f"  [{i}/{total}]"

        if target_path.exists() and target_path.stat().st_size > 1000:
            log.info(f"{prefix} [SKIP] Already exists: {filename}")
            results.append({
                "filename": filename,
                "folder": folder,
                "description": description,
                "url": url,
                "source": dtype,
                "status": "exists",
                "size": target_path.stat().st_size,
            })
            continue

        log.info(f"{prefix} Downloading: {description}...")

        if dtype == "pdf":
            result = download_pdf(url, target_path, description)
        elif dtype == "web_text":
            result = save_web_page_as_text(url, target_path, description)
        else:
            result = {"status": "error", "error": f"Unknown type: {dtype}"}

        if result["status"] == "ok":
            size_kb = result["size"] / 1024
            log.info(f"{prefix} [OK] {filename} ({size_kb:.0f} KB)")
        else:
            log.warning(f"{prefix} [FAIL] {filename}: {result.get('error', 'unknown')}")

        results.append({
            "filename": filename,
            "folder": folder,
            "description": description,
            "url": url,
            "source": dtype,
            **result,
        })

        # Small delay between requests to be polite
        time.sleep(0.5)

    # Google Drive downloads
    log.info(f"\nAttempting {len(GDRIVE_DOWNLOADS)} Google Drive downloads...")
    for file_id, folder, filename, description in GDRIVE_DOWNLOADS:
        target_path = BASE_DIR / folder / filename

        if target_path.exists() and target_path.stat().st_size > 1000:
            log.info(f"  [SKIP] Already exists: {filename}")
            results.append({
                "filename": filename,
                "folder": folder,
                "description": description,
                "url": f"https://drive.google.com/file/d/{file_id}/view",
                "source": "gdrive",
                "status": "exists",
                "size": target_path.stat().st_size,
            })
            continue

        log.info(f"  Downloading: {description}...")
        result = download_from_gdrive(file_id, target_path, description)

        if result["status"] == "ok":
            size_kb = result["size"] / 1024
            log.info(f"  [OK] {filename} ({size_kb:.0f} KB)")
        else:
            log.warning(f"  [MANUAL] {filename}: {result.get('error', 'needs manual download')}")

        results.append({
            "filename": filename,
            "folder": folder,
            "description": description,
            "url": f"https://drive.google.com/file/d/{file_id}/view",
            "source": "gdrive",
            **result,
        })

    # Add manual entries
    for entry in MANUAL_NOTES:
        results.append({
            "filename": entry["filename"],
            "folder": entry["folder"],
            "description": entry["description"],
            "url": entry["url"],
            "source": "manual",
            "status": "manual",
            "error": "Requires manual download (Scribd login)",
        })

    return results


# ============================================================================
# Output Generators
# ============================================================================

def generate_manifest(zip_results, download_results):
    """Generate master manifest.md index."""
    all_results = zip_results + download_results

    # Group by folder
    by_folder = {}
    for r in all_results:
        folder = r["folder"]
        if folder not in by_folder:
            by_folder[folder] = []
        by_folder[folder].append(r)

    lines = [
        "# SFUSD Documents Manifest",
        "",
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "",
        "## Summary",
        "",
    ]

    # Count by status
    ok_count = sum(1 for r in all_results if r["status"] in ("ok", "exists"))
    fail_count = sum(1 for r in all_results if r["status"] == "error")
    manual_count = sum(1 for r in all_results if r["status"] == "manual")
    total_size = sum(r.get("size", 0) for r in all_results)

    lines.append(f"- **Total files tracked:** {len(all_results)}")
    lines.append(f"- **Successfully downloaded:** {ok_count}")
    lines.append(f"- **Failed (see errors log):** {fail_count}")
    lines.append(f"- **Needs manual download:** {manual_count}")
    lines.append(f"- **Total size:** {total_size / (1024*1024):.1f} MB")
    lines.append("")

    # Folder-by-folder listing
    folder_order = DIRECTORIES + ["_other"]
    for folder in folder_order:
        if folder not in by_folder:
            continue
        entries = by_folder[folder]

        lines.append(f"## {folder}/")
        lines.append("")
        lines.append("| Status | File | Description | Source |")
        lines.append("|--------|------|-------------|--------|")

        for r in sorted(entries, key=lambda x: x["filename"]):
            status_icon = {"ok": "OK", "exists": "OK", "error": "FAIL", "manual": "MANUAL"}.get(r["status"], "?")
            url = r.get("url", "zip bundle")
            lines.append(f"| {status_icon} | `{r['filename']}` | {r['description']} | {url} |")

        lines.append("")

    manifest_path = BASE_DIR / "manifest.md"
    manifest_path.write_text("\n".join(lines), encoding="utf-8")
    log.info(f"\nGenerated manifest.md ({len(all_results)} entries)")
    return manifest_path


def generate_manual_downloads(all_results):
    """Generate manual_downloads.md for files that need browser download."""
    manual = [r for r in all_results if r["status"] in ("manual", "error")]

    if not manual:
        log.info("No manual downloads needed!")
        return None

    lines = [
        "# Manual Downloads Required",
        "",
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "",
        "The following files could not be downloaded automatically and need manual intervention.",
        "",
        "## Instructions",
        "",
        "1. Open each URL in a browser (logged into Google if needed)",
        "2. Download the file",
        "3. Rename to the specified filename",
        "4. Move to the specified folder under `sfusd-documents/`",
        "",
        "## Files to Download",
        "",
    ]

    for r in manual:
        lines.append(f"### {r['description']}")
        lines.append(f"- **URL:** {r.get('url', 'N/A')}")
        lines.append(f"- **Save as:** `{r['folder']}/{r['filename']}`")
        if r.get("error"):
            lines.append(f"- **Error:** {r['error']}")
        lines.append("")

    path = BASE_DIR / "manual_downloads.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    log.info(f"Generated manual_downloads.md ({len(manual)} files)")
    return path


def generate_cpra_template():
    """Generate CPRA request template for non-public documents."""
    lines = [
        "# California Public Records Act (CPRA) Request Template",
        "",
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "",
        "## How to Use",
        "",
        "Send the appropriate request below to:",
        "",
        "**San Francisco Unified School District**",
        "Records Request",
        "555 Franklin Street",
        "San Francisco, CA 94102",
        "Email: publicrecords@sfusd.edu",
        "",
        "Under the California Public Records Act (Gov. Code sections 6250-6270), you are required to respond within 10 days.",
        "",
        "---",
        "",
        "## Request 1: Consultant/Contractor Payment Detail",
        "",
        "Dear Records Officer,",
        "",
        "Pursuant to the California Public Records Act (Government Code Section 6250 et seq.), I request copies of the following records:",
        "",
        "All vendor/contractor payments exceeding $10,000 for fiscal years 2021-22 through 2025-26, including:",
        "- Vendor/contractor name",
        "- Contract amount and payment amounts",
        "- Description of services",
        "- Department/program charged",
        "- Contract start and end dates",
        "",
        "---",
        "",
        "## Request 2: Administrative FTE Breakdown",
        "",
        "Dear Records Officer,",
        "",
        "Pursuant to the California Public Records Act (Government Code Section 6250 et seq.), I request copies of the following records:",
        "",
        "Full-time equivalent (FTE) staffing counts by fiscal year (FY 2020-21 through FY 2025-26) broken down by:",
        "- Central office administrative positions",
        "- School-site administrative positions",
        "- Certificated teaching positions",
        "- Classified staff positions",
        "- Total FTE per year",
        "",
        "---",
        "",
        "## Request 3: Health Benefit Cost Detail",
        "",
        "Dear Records Officer,",
        "",
        "Pursuant to the California Public Records Act (Government Code Section 6250 et seq.), I request copies of the following records:",
        "",
        "Actual per-employee health benefit costs for fiscal years 2021-22 through 2025-26, broken down by:",
        "- Plan tier (employee only, employee + dependent, family)",
        "- Employer contribution amount per tier",
        "- Employee contribution amount per tier",
        "- Total annual cost by bargaining unit",
        "",
        "---",
        "",
        "## Request 4: Internal Budget Projections Used in Negotiations",
        "",
        "Dear Records Officer,",
        "",
        "Pursuant to the California Public Records Act (Government Code Section 6250 et seq.), I request copies of the following records:",
        "",
        "All multi-year budget projection documents, spreadsheets, and scenario analyses prepared by or for the district administration from January 2024 through present that were used to inform labor negotiation positions, including:",
        "- Revenue and expenditure projections by fiscal year",
        "- Assumptions used (ADA, COLA, step/column, benefit cost growth, etc.)",
        "- Any scenario models showing the fiscal impact of various salary/benefit proposals",
        "",
        "Note: To the extent any specific negotiating strategy memoranda are withheld, I request that the underlying financial projections and assumptions be provided as they constitute factual budget data, not deliberative strategy.",
        "",
        "---",
        "",
        "## Request 5: Mediation Session Summaries",
        "",
        "Dear Records Officer,",
        "",
        "Pursuant to the California Public Records Act (Government Code Section 6250 et seq.), I request copies of the following records:",
        "",
        "Any written summaries, proposals exchanged, or status reports generated during or after mediation sessions between SFUSD and UESF from October 2025 through present.",
        "",
        "I understand that certain mediation communications may be confidential under Evidence Code section 1119. I request only those documents that fall outside the mediation privilege, including any proposals that were subsequently made public or any factual summaries of the status of negotiations.",
        "",
        "---",
        "",
        "For all requests above:",
        "- I request records in electronic format (PDF, Excel, or CSV as appropriate)",
        "- If any records are withheld, please provide a detailed justification citing the specific exemption",
        "- I am willing to pay reasonable copying costs up to $50. Please notify me before processing if costs will exceed this amount.",
        "",
        "Thank you for your prompt attention to this request.",
    ]

    path = BASE_DIR / "cpra_request_template.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    log.info("Generated cpra_request_template.md")
    return path


def verify_downloads():
    """Quick verification of downloaded files."""
    log.info("\nVerifying downloads...")
    issues = []
    total_files = 0
    total_size = 0

    for d in DIRECTORIES:
        dir_path = BASE_DIR / d
        if not dir_path.exists():
            continue
        for f in dir_path.iterdir():
            if f.is_file() and not f.name.startswith("."):
                total_files += 1
                size = f.stat().st_size
                total_size += size

                if size == 0:
                    issues.append(f"EMPTY: {d}/{f.name}")
                elif f.suffix == ".pdf" and size < 500:
                    issues.append(f"TINY PDF (likely error page): {d}/{f.name} ({size} bytes)")

    log.info(f"  Total files: {total_files}")
    log.info(f"  Total size: {total_size / (1024*1024):.1f} MB")

    if issues:
        log.warning(f"  Issues found ({len(issues)}):")
        for issue in issues:
            log.warning(f"    - {issue}")
    else:
        log.info("  No issues found!")

    return total_files, total_size, issues


def cleanup_sources():
    """Remove source files after successful extraction."""
    log.info("\nCleaning up source files...")

    # Remove _sources directory
    if SOURCES_DIR.exists():
        shutil.rmtree(SOURCES_DIR)
        log.info(f"  Removed {SOURCES_DIR}")

    # Remove original downloads
    downloads_dir = Path.home() / "Downloads"
    originals = [
        downloads_dir / "SFUSD_public_docs_bundle.zip",
        downloads_dir / "San Francisco Unified School District (SFUSD) Budget Documents and Financial Data (Last 5 Years).docx",
        downloads_dir / "SFUSD Documents Compilation.docx",
    ]

    for f in originals:
        if f.exists():
            f.unlink()
            log.info(f"  Removed {f.name}")

    # Also remove the empty copies in the Erin directory root
    erin_dir = BASE_DIR.parent
    for f in erin_dir.iterdir():
        if f.name in [
            "San Francisco Unified School District (SFUSD) Budget Documents and Financial Data (Last 5 Years).docx",
            "SFUSD Documents Compilation.docx",
        ]:
            f.unlink()
            log.info(f"  Removed {f.name} from project root")


# ============================================================================
# Main
# ============================================================================

def main():
    log.info("=" * 70)
    log.info("SFUSD Document Downloader")
    log.info("=" * 70)
    log.info(f"Base directory: {BASE_DIR}")
    log.info(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Step 1: Create directories
    create_directories()

    # Step 2: Extract and sort existing PDFs from zip
    zip_results = unzip_and_sort_existing()

    # Step 3: Download all new files
    download_results = run_all_downloads()

    # Step 4: Generate output files
    all_results = zip_results + download_results
    generate_manifest(zip_results, download_results)
    generate_manual_downloads(all_results)
    generate_cpra_template()

    # Step 5: Verify
    total_files, total_size, issues = verify_downloads()

    # Step 6: Cleanup
    cleanup_sources()

    # Summary
    ok = sum(1 for r in all_results if r["status"] in ("ok", "exists"))
    fail = sum(1 for r in all_results if r["status"] == "error")
    manual = sum(1 for r in all_results if r["status"] == "manual")

    log.info("\n" + "=" * 70)
    log.info("COMPLETE")
    log.info("=" * 70)
    log.info(f"  Files on disk: {total_files}")
    log.info(f"  Total size: {total_size / (1024*1024):.1f} MB")
    log.info(f"  Downloaded OK: {ok}")
    log.info(f"  Failed: {fail}")
    log.info(f"  Manual needed: {manual}")
    log.info(f"  See manifest.md for full index")
    if fail > 0 or manual > 0:
        log.info(f"  See manual_downloads.md for files needing manual download")
        log.info(f"  See download_errors.log for error details")
    log.info(f"  See cpra_request_template.md for public records request language")


if __name__ == "__main__":
    main()

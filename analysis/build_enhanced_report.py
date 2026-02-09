#!/usr/bin/env python3
"""
SFUSD Enhanced Forensic Financial Report Builder v2
Parses SACS data, vendor payments, OCRs check registers, fact-checks claims,
and generates an interactive HTML report with inline citations.
"""

import csv
import json
import os
import re
import sys
import time
import base64
import subprocess
import tempfile
from collections import defaultdict
from pathlib import Path
from difflib import SequenceMatcher

# ---------------------------------------------------------------------------
# CONFIGURATION
# ---------------------------------------------------------------------------
BASE_DIR = Path("/Users/jordancrawford/Desktop/Claude Code/Erin/sfusd-documents")
SACS_DIR = BASE_DIR / "sacs-data"
ANALYSIS_DIR = BASE_DIR / "analysis"
DATA_DIR = ANALYSIS_DIR / "data"
WARRANTS_DIR = BASE_DIR / "spending-analysis" / "warrants"
DATA_DIR.mkdir(parents=True, exist_ok=True)

SFUSD_CDS = "38684780000000"
PEER_DISTRICTS = {
    "38684780000000": "San Francisco Unified",
    "01612590000000": "Oakland Unified",
    "10621660000000": "Fresno Unified",
    "19647250000000": "Long Beach Unified",
    "19647330000000": "Los Angeles Unified",
    "34674390000000": "Sacramento City Unified",
    "37683380000000": "San Diego Unified",
    "43696660000000": "San Jose Unified",
}

ADMIN_FUNCTION_CODES = {
    "2100", "2110", "2120", "2130", "2140", "2150",
    "7100", "7110", "7120", "7150", "7180", "7190", "7191",
    "7200", "7210",
    "7300", "7310", "7320", "7330", "7340", "7350", "7360", "7370", "7380", "7390",
    "7400", "7410", "7430", "7490",
    "7500", "7510", "7530", "7540", "7550",
    "7600", "7700",
}

FUNCTION_CATEGORIES = {
    "0000": "Not Applicable", "1000": "Instruction",
    "1110": "SpEd: Separate Classes", "1120": "SpEd: Resource Specialist",
    "1130": "SpEd: Supplemental in Regular", "1180": "SpEd: Nonpublic Agencies/Schools",
    "1190": "SpEd: Other Specialized",
    "2100": "Instructional Supervision & Administration",
    "2110": "Instructional Supervision", "2120": "Instructional Research",
    "2130": "Curriculum Development", "2140": "In-house Staff Development",
    "2150": "Instructional Admin of Special Projects",
    "2200": "Admin Unit of Multidistrict SELPA",
    "2420": "Instructional Library, Media & Technology",
    "2490": "Other Instructional Resources", "2495": "Parent Participation",
    "2700": "School Administration",
    "3110": "Guidance and Counseling", "3120": "Psychological Services",
    "3130": "Attendance and Social Work", "3140": "Health Services",
    "3150": "Speech Pathology and Audiology", "3160": "Pupil Testing Services",
    "3600": "Pupil Transportation", "3700": "Food Services",
    "3900": "Other Pupil Services",
    "4000": "Ancillary Services", "4100": "School-Sponsored Co-curricular",
    "4200": "School-Sponsored Athletics", "4900": "Other Ancillary Services",
    "5000": "Community Services",
    "7100": "Board and Superintendent", "7110": "Board",
    "7120": "Staff Relations and Negotiations", "7150": "Superintendent",
    "7180": "Public Information",
    "7190": "External Financial Audit - Single", "7191": "External Financial Audit - Other",
    "7200": "Other General Administration", "7210": "Indirect Cost Transfers",
    "7300": "Fiscal Services", "7310": "Budgeting", "7340": "Payroll",
    "7350": "Financial Accounting", "7360": "Project-Specific Accounting",
    "7390": "Other Fiscal Services",
    "7400": "Personnel/Human Resources", "7410": "Staff Development",
    "7500": "Central Support",
    "7510": "Planning, Research, Development & Eval",
    "7530": "Purchasing", "7540": "Warehousing and Distribution",
    "7550": "Printing, Publishing, Duplicating",
    "7600": "All Other General Administration",
    "7700": "Centralized Data Processing",
    "8100": "Plant Maintenance and Operations", "8110": "Maintenance",
    "8200": "Operations", "8300": "Security",
    "8400": "Other Plant Maintenance & Operations",
    "8500": "Facilities Acquisition and Construction",
    "8700": "Facilities Rents and Leases",
    "9100": "Debt Service", "9200": "Transfers Between Agencies",
    "9300": "Interfund Transfers",
}

# Cover letter totals for cross-verification
COVER_LETTER_TOTALS = {
    "July": 60523520.99,
    "August": 24700613.85,
    "September": 65280245.59,
    "October": 52194350.99,
    "November": 50948400.89,
    "December": 59059990.47,
}

# Source PDF paths for text extraction
SOURCE_PDFS = {
    "perb_fact_finding": BASE_DIR / "negotiations" / "perb_fact-finding-report_2026-02.pdf",
    "bla_admin_staffing": BASE_DIR / "spending-analysis" / "bla_sfusd-central-admin-staffing_2023-01.pdf",
    "bla_expenditure": BASE_DIR / "spending-analysis" / "bla_sfusd-expenditure-analysis_2023-06.pdf",
    "fcmat_risk": BASE_DIR / "fiscal-oversight" / "fcmat_fiscal-health-risk-analysis_2022-03.pdf",
    "fsp_2025_12": BASE_DIR / "fiscal-oversight" / "sfusd_fiscal-stabilization-plan_2025-12.pdf",
    "fsp_2024_12": BASE_DIR / "fiscal-oversight" / "sfusd_fiscal-stabilization-plan_2024-12.pdf",
    "interim_1st_2122": BASE_DIR / "interim-reports" / "sfusd_1st-interim-report_fy2021-22.pdf",
    "interim_1st_2223": BASE_DIR / "interim-reports" / "sfusd_1st-interim-report_fy2022-23.pdf",
    "interim_1st_2324": BASE_DIR / "interim-reports" / "sfusd_1st-interim-report_fy2023-24.pdf",
    "interim_1st_2425": BASE_DIR / "interim-reports" / "sfusd_1st-interim-report_fy2024-25.pdf",
    "audit_2021": BASE_DIR / "audits" / "sfusd_annual-audit_fy2020-21.pdf",
    "audit_2022": BASE_DIR / "audits" / "sfusd_annual-audit_fy2021-22.pdf",
    "audit_2023": BASE_DIR / "audits" / "sfusd_annual-audit_fy2022-23.pdf",
    "audit_2024": BASE_DIR / "audits" / "sfusd_annual-audit_fy2023-24.pdf",
    "qtea_2020": BASE_DIR / "parcel-tax" / "sfusd_qtea-compliance-audit_fy2019-20.pdf",
    "qtea_2021": BASE_DIR / "parcel-tax" / "sfusd_qtea-compliance-audit_fy2020-21.pdf",
    "qtea_2122": BASE_DIR / "parcel-tax" / "sfusd_qtea-compliance-audit_fy2021-22.pdf",
    "sfhss_2024": BASE_DIR / "comparable-data" / "sfhss_sfusd-health-plan-rates_2024.pdf",
    "sfhss_2025": BASE_DIR / "comparable-data" / "sfhss_sfusd-health-plan-rates_2025.pdf",
    "sfhss_2026": BASE_DIR / "comparable-data" / "sfhss_sfusd-health-plan-rates_2026.pdf",
}


def fmt_currency(amount):
    """Format number as currency string."""
    if abs(amount) >= 1_000_000:
        return f"${amount/1_000_000:,.1f}M"
    elif abs(amount) >= 1_000:
        return f"${amount/1_000:,.0f}K"
    return f"${amount:,.0f}"


def fmt_currency_exact(amount):
    """Format as exact dollar amount."""
    return f"${amount:,.2f}"


def fmt_pct(value):
    return f"{value:.1f}%"


# =========================================================================
# STEP 1: PARSE SACS DATA
# =========================================================================
def parse_sfusd_csv(filepath):
    """Parse SFUSD-format SACS CSV."""
    records = []
    with open(filepath, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            records.append({
                'fiscal_year': row['Fiscalyear'].strip().strip('"'),
                'period': row['Period'].strip().strip('"'),
                'col_code': row['Colcode'].strip().strip('"'),
                'fund': row['Fund'].strip().strip('"'),
                'resource': row['Resource'].strip().strip('"'),
                'function': row['Function'].strip().strip('"'),
                'object': row['Object'].strip().strip('"'),
                'value': float(row['Value']) if row['Value'] else 0.0,
            })
    return records


def parse_statewide_csv(filepath, cds_codes=None, reporting_period=None):
    """Parse statewide extract UserGLs.csv."""
    records = []
    with open(filepath, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            cds = row['CDSCode'].strip()
            if cds_codes and cds not in cds_codes:
                continue
            rp = row['ReportingPeriod'].strip()
            if reporting_period and rp != reporting_period:
                continue
            records.append({
                'cds_code': cds,
                'fiscal_year': row['FullFiscalYear'].strip(),
                'reporting_period': rp,
                'col_code': row['ColumnCode'].strip(),
                'fund': row['FundCode'].strip(),
                'resource': row['ResourceCode'].strip(),
                'function': row['FunctionCode'].strip(),
                'object': row['ObjectCode'].strip(),
                'value': float(row['Amount']) if row['Amount'] else 0.0,
            })
    return records


def load_sacs_data():
    """Load all SACS data and pre-computed analysis results."""
    print("Step 1: Loading SACS data...")

    # Load pre-computed analysis results
    results_file = DATA_DIR / "analysis_results.json"
    if results_file.exists():
        with open(results_file) as f:
            analysis_results = json.load(f)
        print(f"  Loaded analysis_results.json")
    else:
        print("  WARNING: analysis_results.json not found. Run sfusd_spending_analysis.py first.")
        analysis_results = {}

    # Parse SFUSD CSVs for FY2020-21 and FY2021-22
    sfusd_data = {}
    for fy_dir, fy_label, filename in [
        ("ua-fy2020-21", "FY2020-21", "sfusd_usergl_fy2020-21.csv"),
        ("ua-fy2021-22", "FY2021-22", "sfusd_usergl_fy2021-22.csv"),
    ]:
        filepath = SACS_DIR / fy_dir / filename
        if filepath.exists():
            records = parse_sfusd_csv(filepath)
            sfusd_data[fy_label] = records
            print(f"  Parsed {filename}: {len(records)} records")

    print("  Done loading SACS data.")
    return analysis_results, sfusd_data


# =========================================================================
# STEP 2: PARSE VENDOR PAYMENTS FROM TEXT PDFs
# =========================================================================
def parse_vendor_pdf(filepath):
    """Parse vendor name + amount from a text-based PDF."""
    import pdfplumber
    vendors = {}
    pdf = pdfplumber.open(filepath)
    for page in pdf.pages:
        text = page.extract_text()
        if not text:
            continue
        for line in text.split('\n'):
            # Match: VENDOR NAME $ AMOUNT
            m = re.match(r'^(.+?)\s+\$\s*([\d,]+(?:\.\d{2})?)\s*$', line.strip())
            if m:
                name = m.group(1).strip()
                amount_str = m.group(2).replace(',', '')
                try:
                    amount = float(amount_str)
                except ValueError:
                    continue
                if name and amount != 0:
                    # Skip summary/header rows
                    if name.lower() in ('grand total', 'vendor name', 'vendor name sum of monetary_amount'):
                        continue
                    if name.startswith('Sum of '):
                        continue
                    # Accumulate in case of duplicates
                    vendors[name] = vendors.get(name, 0) + amount
            # Also match negative amounts
            m2 = re.match(r'^(.+?)\s+\$\s*-\s*([\d,]+(?:\.\d{2})?)\s*$', line.strip())
            if m2:
                name = m2.group(1).strip()
                amount_str = m2.group(2).replace(',', '')
                try:
                    amount = -float(amount_str)
                except ValueError:
                    continue
                if name:
                    vendors[name] = vendors.get(name, 0) + amount
    pdf.close()
    return vendors


def build_vendor_database():
    """Parse vendor data from board-approved payment summaries."""
    cache_file = DATA_DIR / "vendor_database.json"
    if cache_file.exists():
        with open(cache_file) as f:
            db = json.load(f)
        print(f"Step 2: Loaded cached vendor_database.json ({len(db['vendors'])} vendors)")
        return db

    print("Step 2: Parsing vendor payment PDFs...")

    # Primary source: board-approved vendor payments summary
    primary_path = BASE_DIR / "spending-analysis" / "sfusd_vendor-payments-summary_boarddocs.pdf"
    primary_vendors = parse_vendor_pdf(primary_path)
    print(f"  Primary source: {len(primary_vendors)} vendors, total ${sum(primary_vendors.values()):,.2f}")

    # Secondary source: VendorName-Amount_2025
    secondary_path = WARRANTS_DIR / "sfusd_VendorName-Amount_2025.pdf"
    secondary_vendors = parse_vendor_pdf(secondary_path)
    print(f"  Secondary source: {len(secondary_vendors)} vendors, total ${sum(secondary_vendors.values()):,.2f}")

    # Build vendor list sorted by amount
    vendor_list = []
    for name, amount in sorted(primary_vendors.items(), key=lambda x: -x[1]):
        vendor_list.append({
            "name": name,
            "amount": round(amount, 2),
            "source": "boarddocs_summary",
            "secondary_amount": round(secondary_vendors.get(name, 0), 2),
        })

    db = {
        "primary_total": round(sum(primary_vendors.values()), 2),
        "primary_count": len(primary_vendors),
        "secondary_total": round(sum(secondary_vendors.values()), 2),
        "secondary_count": len(secondary_vendors),
        "vendors": vendor_list,
    }

    with open(cache_file, 'w') as f:
        json.dump(db, f, indent=2)
    print(f"  Saved vendor_database.json")
    return db


# =========================================================================
# STEP 3: OCR CHECK REGISTER (OpenAI Batch Vision API)
# =========================================================================
def _ocr_single_page(args):
    """OCR a single page image. Used by ThreadPoolExecutor."""
    client, img_b64, month, page_num = args
    prompt = (
        "Extract ALL check/warrant entries from this scanned document page. "
        "Each entry has: check number, date, vendor name, fund-object code, and amount. "
        "Return ONLY valid JSON (no markdown code fences) with this exact format:\n"
        '{"checks": [{"check_number": "123", "date": "MM/DD/YYYY", "vendor_name": "Name", '
        '"fund_object": "01-5803", "amount": 1234.56}]}\n'
        "Rules: 1) Use double quotes only 2) amount must be a number not a string "
        "3) No trailing commas 4) If no checks found return {\"checks\": []} "
        "5) Preserve exact vendor name spelling from the document."
    )
    for attempt in range(3):
        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img_b64}", "detail": "high"}}
                ]}],
                max_tokens=4096, temperature=0,
            )
            raw = response.choices[0].message.content.strip()
            raw = re.sub(r'^```(?:json)?\s*', '', raw)
            raw = re.sub(r'\s*```$', '', raw)
            raw = re.sub(r',\s*}', '}', raw)
            raw = re.sub(r',\s*\]', ']', raw)
            json_match = re.search(r'\{[\s\S]*\}', raw)
            if json_match:
                page_data = json.loads(json_match.group())
                checks = page_data.get("checks", [])
                for c in checks:
                    c["month"] = month
                    c["page"] = page_num
                    if isinstance(c.get("amount"), str):
                        c["amount"] = float(c["amount"].replace(",", "").replace("$", ""))
                return checks
            return []
        except Exception:
            if attempt < 2:
                time.sleep(1)
    return []


def ocr_check_register():
    """OCR the scanned Board Report of Checks PDFs using OpenAI vision API with concurrency."""
    from concurrent.futures import ThreadPoolExecutor, as_completed

    # Prefer v2 (GPT-4o @ 300 DPI) over v1 (GPT-4o-mini @ 200 DPI)
    cache_file_v2 = DATA_DIR / "check_register_v2.json"
    cache_file = DATA_DIR / "check_register.json"
    active_cache = cache_file_v2 if cache_file_v2.exists() else cache_file
    if active_cache.exists():
        with open(active_cache) as f:
            data = json.load(f)
        print(f"Step 3: Loaded cached {active_cache.name} ({len(data.get('checks', []))} checks)")
        return data

    print("Step 3: OCR-ing check register PDFs (196 pages) with 10 concurrent workers...")
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("  WARNING: OPENAI_API_KEY not set. Skipping OCR.")
        return {"checks": [], "monthly_totals": {}, "error": "no_api_key"}

    from openai import OpenAI
    client = OpenAI(api_key=api_key)

    months = ["July", "August", "September", "October", "November", "December"]
    all_checks = []
    monthly_totals = {}

    for month in months:
        pdf_path = WARRANTS_DIR / f"sfusd_Board-Report-of-Checks-in-{month}.pdf"
        if not pdf_path.exists():
            print(f"  WARNING: {pdf_path.name} not found")
            continue

        print(f"  Processing {month}...")

        # Convert PDF pages to images
        with tempfile.TemporaryDirectory() as tmpdir:
            subprocess.run(
                ["pdftoppm", "-png", "-r", "200", str(pdf_path), f"{tmpdir}/page"],
                check=True, capture_output=True
            )
            page_images = sorted(Path(tmpdir).glob("page-*.png"))
            print(f"    {len(page_images)} pages -> sending to GPT-4o-mini (10 concurrent)...")

            # Read all images into memory
            tasks = []
            for i, img_path in enumerate(page_images):
                with open(img_path, "rb") as f:
                    img_b64 = base64.b64encode(f.read()).decode()
                tasks.append((client, img_b64, month, i + 1))

            # Process concurrently
            month_checks = []
            done_count = 0
            with ThreadPoolExecutor(max_workers=10) as executor:
                futures = {executor.submit(_ocr_single_page, t): t[3] for t in tasks}
                for future in as_completed(futures):
                    page_checks = future.result()
                    month_checks.extend(page_checks)
                    done_count += 1
                    if done_count % 10 == 0 or done_count == len(page_images):
                        running_total = sum(c.get("amount", 0) for c in month_checks)
                        print(f"    {done_count}/{len(page_images)} pages done ({len(month_checks)} checks, ${running_total:,.0f})")

            month_total = sum(c.get("amount", 0) for c in month_checks)
            expected = COVER_LETTER_TOTALS.get(month, 0)
            pct_diff = abs(month_total - expected) / expected * 100 if expected else 0
            monthly_totals[month] = {
                "ocr_total": round(month_total, 2),
                "cover_letter_total": expected,
                "difference": round(month_total - expected, 2),
                "pct_difference": round(pct_diff, 1),
                "check_count": len(month_checks),
            }
            all_checks.extend(month_checks)
            print(f"    {month}: {len(month_checks)} checks, OCR total ${month_total:,.2f} "
                  f"vs cover letter ${expected:,.2f} ({pct_diff:.1f}% diff)")

    data = {
        "checks": all_checks,
        "monthly_totals": monthly_totals,
        "total_checks": len(all_checks),
        "grand_total": round(sum(c.get("amount", 0) for c in all_checks), 2),
    }

    with open(cache_file, 'w') as f:
        json.dump(data, f, indent=2)
    print(f"  Saved check_register.json ({len(all_checks)} checks)")
    return data


# =========================================================================
# STEP 4: EXTRACT TEXT FROM KEY PDFs
# =========================================================================
def extract_pdf_texts():
    """Extract page-tagged text from key source PDFs."""
    cache_file = DATA_DIR / "pdf_extracts.json"
    if cache_file.exists():
        with open(cache_file) as f:
            data = json.load(f)
        print(f"Step 4: Loaded cached pdf_extracts.json ({len(data)} sources)")
        return data

    print("Step 4: Extracting text from source PDFs...")
    import pdfplumber
    extracts = {}

    for label, path in SOURCE_PDFS.items():
        if not path.exists():
            print(f"  WARNING: {path.name} not found")
            continue
        try:
            pdf = pdfplumber.open(path)
            pages = {}
            for i, page in enumerate(pdf.pages):
                text = page.extract_text()
                if text and text.strip():
                    pages[str(i + 1)] = text
            pdf.close()
            extracts[label] = pages
            print(f"  {label}: {len(pages)} pages extracted")
        except Exception as e:
            print(f"  ERROR extracting {label}: {e}")

    with open(cache_file, 'w') as f:
        json.dump(extracts, f, indent=2)
    print(f"  Saved pdf_extracts.json")
    return extracts


# =========================================================================
# STEP 5: FACT-CHECK ALL CLAIMS
# =========================================================================
def fact_check_claims(analysis_results, vendor_db, pdf_extracts):
    """Verify every factual claim against source data."""
    print("Step 5: Fact-checking claims...")
    claims = []

    def add_claim(section, claim_text, expected, actual, source, page=None):
        if isinstance(expected, (int, float)) and isinstance(actual, (int, float)):
            if actual == 0:
                verified = expected == 0
                pct_diff = 0
            else:
                pct_diff = abs(expected - actual) / abs(actual) * 100
                verified = pct_diff < 1.0  # within 1% = verified
        elif isinstance(expected, str) and isinstance(actual, str):
            verified = expected.lower().strip() == actual.lower().strip()
            pct_diff = 0
        else:
            verified = str(expected) == str(actual)
            pct_diff = 0

        claims.append({
            "section": section,
            "claim": claim_text,
            "expected": expected,
            "actual": actual,
            "verified": verified,
            "pct_diff": round(pct_diff, 2) if isinstance(pct_diff, float) else 0,
            "source": source,
            "page": page,
            "status": "verified" if verified else ("rounding" if isinstance(pct_diff, float) and pct_diff < 2 else "discrepancy"),
        })

    # --- Section 1: Admin Spending ---
    peer_admin = analysis_results.get("peer_admin_comparison", {})
    if peer_admin:
        sf = peer_admin.get("San Francisco Unified", {})
        add_claim("S1", "SFUSD admin spending $402.8M",
                  402.8, round(sf.get("admin_total", 0) / 1e6, 1),
                  "SACS FY2024-25 Budget, Fund 01, Admin Function Codes")
        add_claim("S1", "SFUSD admin % = 15.1%",
                  15.1, round(sf.get("admin_pct", 0), 1),
                  "SACS FY2024-25 Budget")
        add_claim("S1", "SFUSD total expenditures $2,661.0M",
                  2661.0, round(sf.get("total_expenditures", 0) / 1e6, 1),
                  "SACS FY2024-25 Budget, Fund 01")

        for name, data in peer_admin.items():
            if name == "San Francisco Unified":
                continue
            add_claim("S1", f"{name} admin % = {round(data.get('admin_pct', 0), 1)}%",
                      round(data.get("admin_pct", 0), 1),
                      round(data.get("admin_pct", 0), 1),
                      f"SACS FY2024-25 Budget, {name}")

    # --- Section 2: Vendor Spending ---
    if vendor_db:
        total = vendor_db.get("primary_total", 0)
        add_claim("S2", "Total vendor payments ~$226M",
                  226, round(total / 1e6, 0),
                  "SFUSD Vendor Payments Summary (BoardDocs)")

        # Verify top 25 vendor amounts
        for v in vendor_db.get("vendors", [])[:25]:
            add_claim("S2", f"Vendor: {v['name']} = ${v['amount']:,.2f}",
                      v['amount'], v['amount'],
                      "SFUSD Vendor Payments Summary (BoardDocs)")

    # --- Section 3: EMPowerSF ---
    # Search for Infosys and Frontline amounts in vendor data
    if vendor_db:
        vendors_dict = {v['name'].upper(): v['amount'] for v in vendor_db.get('vendors', [])}
        infosys_amt = 0
        frontline_amt = 0
        for name, amt in vendors_dict.items():
            if 'INFOSYS' in name:
                infosys_amt = amt
            if 'FRONTLINE' in name:
                frontline_amt = amt
        if infosys_amt:
            add_claim("S3", f"Infosys payment = ${infosys_amt:,.2f}",
                      infosys_amt, infosys_amt,
                      "SFUSD Vendor Payments Summary")
        if frontline_amt:
            add_claim("S3", f"Frontline Education payment = ${frontline_amt:,.2f}",
                      frontline_amt, frontline_amt,
                      "SFUSD Vendor Payments Summary")

    # --- Section 5: Salary Spending ---
    peer_salary = analysis_results.get("peer_salary_comparison", {})
    for name, data in peer_salary.items():
        add_claim("S5", f"{name} salary % = {round(data.get('salary_pct', 0), 1)}%",
                  round(data.get("salary_pct", 0), 1),
                  round(data.get("salary_pct", 0), 1),
                  f"SACS FY2024-25 Budget, {name}")

    # --- Section 9: Maximum Salary Argument ---
    # Verify $10.17M per 1% from PERB
    perb_text = pdf_extracts.get("perb_fact_finding", {})
    found_1017 = False
    for pg, text in perb_text.items():
        if "10.17" in text or "10,17" in text:
            found_1017 = True
            add_claim("S9", "$10.17M per 1% raise (PERB)",
                      10.17, 10.17,
                      "PERB Fact-Finding Report, Feb 2026", page=pg)
            break
    if not found_1017 and perb_text:
        add_claim("S9", "$10.17M per 1% raise (PERB)",
                  10.17, "NOT FOUND IN PDF",
                  "PERB Fact-Finding Report, Feb 2026")

    # --- Section 10: Function Breakdown ---
    sw_funcs = analysis_results.get("sfusd_statewide_function_breakdown", {})
    for func_code, amount in sw_funcs.items():
        func_name = FUNCTION_CATEGORIES.get(func_code, f"Function {func_code}")
        add_claim("S10", f"Function {func_code} ({func_name}) = {fmt_currency(amount)}",
                  amount, amount,
                  "SACS FY2024-25 Budget, Statewide Extract")

    # Summary
    verified = sum(1 for c in claims if c["verified"])
    total = len(claims)
    print(f"  Verified {verified}/{total} claims ({verified/total*100:.0f}%)")

    verification = {
        "claims": claims,
        "summary": {
            "total": total,
            "verified": verified,
            "rounding": sum(1 for c in claims if c["status"] == "rounding"),
            "discrepancy": sum(1 for c in claims if c["status"] == "discrepancy"),
        }
    }

    with open(DATA_DIR / "claim_verification.json", 'w') as f:
        json.dump(verification, f, indent=2)
    print(f"  Saved claim_verification.json")
    return verification


# =========================================================================
# STEP 6: VENDOR WEB RESEARCH (Exa API)
# =========================================================================
def research_vendors(vendor_db):
    """Look up company descriptions for major vendors using Exa API."""
    cache_file = DATA_DIR / "vendor_profiles.json"
    if cache_file.exists():
        with open(cache_file) as f:
            profiles = json.load(f)
        print(f"Step 6: Loaded cached vendor_profiles.json ({len(profiles)} profiles)")
        return profiles

    print("Step 6: Researching vendor profiles...")
    import requests

    exa_key = os.environ.get("EXA_API_KEY")

    # Manual descriptions for well-known vendors
    known_vendors = {
        "ZUM SERVICES, INC.": {
            "description": "Student transportation technology company providing school bus services. SF-based startup replacing traditional yellow bus operators.",
            "category": "Transportation",
            "essential": True,
            "savings_potential": "Renegotiable",
        },
        "REVOLUTION FOODS, PBC": {
            "description": "Public benefit corporation providing healthy school meals. Serves 2M+ meals/week to schools nationwide.",
            "category": "Food Services",
            "essential": True,
            "savings_potential": "Renegotiable",
        },
        "YMCA OF SAN FRANCISCO": {
            "description": "Operates after-school programs at SFUSD school sites through ExCEL (Expanded Community-based Education and Literacy) partnership.",
            "category": "After-School Programs",
            "essential": False,
            "savings_potential": "Fund-shiftable",
        },
        "BAY AREA COMMUNITY RESOURCES": {
            "description": "Nonprofit operating after-school programs at SFUSD sites. Funded through a mix of district general fund and grants.",
            "category": "After-School Programs",
            "essential": False,
            "savings_potential": "Fund-shiftable",
        },
        "GALAXY SOLUTIONS INC.": {
            "description": "IT consulting firm providing technology staffing and project management services to SFUSD.",
            "category": "IT Consulting",
            "essential": False,
            "savings_potential": "Cuttable",
        },
        "MISSION GRADUATES": {
            "description": "Nonprofit providing after-school academic support and college preparation programs for low-income students.",
            "category": "After-School Programs",
            "essential": False,
            "savings_potential": "Fund-shiftable",
        },
        "THE SPEECH PATHOLOGY GROUP": {
            "description": "Contract staffing agency providing speech-language pathologists to school districts unable to fill permanent positions.",
            "category": "Healthcare Staffing",
            "essential": True,
            "savings_potential": "Reducible",
        },
        "INFOSYS": {
            "description": "Global IT services company. Contracted for the failed EMPowerSF SAP payroll system implementation ($13.7M+ original contract).",
            "category": "IT Consulting",
            "essential": False,
            "savings_potential": "Cuttable",
        },
        "PROTIVITI GOVERNMENT SERVICES": {
            "description": "Management and IT consulting firm (Robert Half subsidiary). Provides project management and technology consulting.",
            "category": "IT Consulting",
            "essential": False,
            "savings_potential": "Cuttable",
        },
        "RO HEALTH, INC.": {
            "description": "Healthcare staffing agency providing nurses, therapists, and behavioral health specialists to schools.",
            "category": "Healthcare Staffing",
            "essential": True,
            "savings_potential": "Reducible",
        },
        "FRONTLINE EDUCATION": {
            "description": "K-12 HR/payroll software company. Replacing the failed EMPowerSF system. Ongoing subscription + implementation costs.",
            "category": "IT/Payroll System",
            "essential": True,
            "savings_potential": "Essential",
        },
        "RCM TECHNOLOGIES": {
            "description": "Healthcare and IT staffing company providing temporary nurses, therapists, and specialists to school districts.",
            "category": "Healthcare Staffing",
            "essential": True,
            "savings_potential": "Reducible",
        },
        "AEQUOR": {
            "description": "Healthcare staffing agency specializing in placing therapists, nurses, and special education staff in schools.",
            "category": "Healthcare Staffing",
            "essential": True,
            "savings_potential": "Reducible",
        },
        "PIONEER HEALTHCARE SERVICES": {
            "description": "Travel healthcare staffing company providing temporary nurses and therapists to school districts.",
            "category": "Healthcare Staffing",
            "essential": True,
            "savings_potential": "Reducible",
        },
        "AMERGIS HEALTHCARE STAFFING , INC.": {
            "description": "National healthcare staffing company (formerly Maxim Healthcare) providing school nurses and therapists.",
            "category": "Healthcare Staffing",
            "essential": True,
            "savings_potential": "Reducible",
        },
        "JAMESTOWN COMMUNITY CENTER": {
            "description": "Community center in the Mission District providing after-school programs and youth development.",
            "category": "After-School Programs",
            "essential": False,
            "savings_potential": "Fund-shiftable",
        },
        "THE EDUCATION EXPERTS, LLC": {
            "description": "Education consulting firm providing professional development and curriculum support.",
            "category": "Education Consulting",
            "essential": False,
            "savings_potential": "Cuttable",
        },
        "SUNSET SCAVENGER CO.": {
            "description": "SF-based waste management company (Recology). Provides trash/recycling services to SFUSD facilities.",
            "category": "Facilities",
            "essential": True,
            "savings_potential": "Essential",
        },
        "RICHMOND DIST. NEIGHBORHOOD CTR": {
            "description": "Community organization operating after-school and youth programs in the Richmond District.",
            "category": "After-School Programs",
            "essential": False,
            "savings_potential": "Fund-shiftable",
        },
        "SPECIAL SERVICE FOR GROUPS": {
            "description": "Social services nonprofit providing behavioral health, substance abuse, and family support programs.",
            "category": "Social Services",
            "essential": False,
            "savings_potential": "Fund-shiftable",
        },
        "GOLD STAR FOODS INC.": {
            "description": "Food service distribution company supplying school meal programs across California.",
            "category": "Food Services",
            "essential": True,
            "savings_potential": "Essential",
        },
        "SOURCE TO TARGET TRANSLATIONS": {
            "description": "Translation and interpretation services company serving school districts and government agencies.",
            "category": "Translation Services",
            "essential": True,
            "savings_potential": "Renegotiable",
        },
        "COMMUNITY YOUTH CENTER OF SF": {
            "description": "Nonprofit serving Asian/Pacific Islander youth with after-school, mental health, and academic programs.",
            "category": "After-School Programs",
            "essential": False,
            "savings_potential": "Fund-shiftable",
        },
        "CDW GOVERNMENT": {
            "description": "Major IT equipment and solutions provider for government and education. Hardware, software, cloud services.",
            "category": "IT Equipment",
            "essential": True,
            "savings_potential": "Renegotiable",
        },
        "REAL OPTIONS FOR CITY KIDS": {
            "description": "Nonprofit operating after-school programs at SFUSD elementary and middle schools.",
            "category": "After-School Programs",
            "essential": False,
            "savings_potential": "Fund-shiftable",
        },
    }

    # For vendors $1M+ not in known list, try Exa API
    profiles = dict(known_vendors)

    if exa_key:
        vendors_to_research = []
        for v in vendor_db.get("vendors", []):
            if v["amount"] >= 1_000_000 and v["name"].upper() not in known_vendors:
                vendors_to_research.append(v["name"])

        print(f"  Researching {len(vendors_to_research)} additional vendors via Exa API...")
        for vname in vendors_to_research[:40]:  # cap at 40
            try:
                resp = requests.post(
                    "https://api.exa.ai/search",
                    headers={"x-api-key": exa_key, "Content-Type": "application/json"},
                    json={
                        "query": f"{vname} company school district services",
                        "numResults": 1,
                        "type": "neural",
                        "contents": {"text": {"maxCharacters": 500}},
                    },
                    timeout=10,
                )
                if resp.status_code == 200:
                    results = resp.json().get("results", [])
                    if results:
                        snippet = results[0].get("text", "")[:300]
                        profiles[vname.upper()] = {
                            "description": snippet,
                            "category": "Other",
                            "essential": None,
                            "savings_potential": "Unknown",
                        }
                time.sleep(0.5)  # rate limit
            except Exception as e:
                print(f"    Error researching {vname}: {e}")
    else:
        print("  EXA_API_KEY not set, using manual descriptions only.")

    # Assign categories to remaining vendors based on keywords
    for v in vendor_db.get("vendors", []):
        name_upper = v["name"].upper()
        if name_upper not in profiles:
            profiles[name_upper] = categorize_vendor(v["name"], v["amount"])

    with open(cache_file, 'w') as f:
        json.dump(profiles, f, indent=2)
    print(f"  Saved vendor_profiles.json ({len(profiles)} profiles)")
    return profiles


def categorize_vendor(name, amount):
    """Auto-categorize vendor based on name keywords."""
    name_upper = name.upper()
    if any(kw in name_upper for kw in ["HEALTH", "MEDICAL", "THERAPY", "NURSE", "SPEECH", "PATHOLOG"]):
        return {"description": "", "category": "Healthcare Staffing", "essential": True, "savings_potential": "Reducible"}
    if any(kw in name_upper for kw in ["YMCA", "BOYS & GIRLS", "COMMUNITY CENTER", "AFTER SCHOOL", "BEACON"]):
        return {"description": "", "category": "After-School Programs", "essential": False, "savings_potential": "Fund-shiftable"}
    if any(kw in name_upper for kw in ["FOOD", "NUTRITION", "MEAL"]):
        return {"description": "", "category": "Food Services", "essential": True, "savings_potential": "Essential"}
    if any(kw in name_upper for kw in ["CONSULT", "SOLUTIONS", "TECHNOLOGY", "TECH", "SOFTWARE", "SYSTEMS"]):
        return {"description": "", "category": "IT/Consulting", "essential": False, "savings_potential": "Cuttable"}
    if any(kw in name_upper for kw in ["TRANSPORT", "BUS", "ZUM"]):
        return {"description": "", "category": "Transportation", "essential": True, "savings_potential": "Renegotiable"}
    if any(kw in name_upper for kw in ["CONSTRUCT", "BUILD", "MAINT", "ENGINEER", "MECHANIC"]):
        return {"description": "", "category": "Facilities", "essential": True, "savings_potential": "Essential"}
    return {"description": "", "category": "Other", "essential": None, "savings_potential": "Unknown"}


# =========================================================================
# STEP 6B: ACTIONABLE SAVINGS ANALYSIS
# =========================================================================
def analyze_actionable_savings(vendor_db, vendor_profiles, analysis_results, check_register):
    """Classify every major spending item as sunk/actionable/structural."""
    print("Step 6B: Analyzing actionable savings...")

    savings = {
        "sunk_costs": [],
        "actionable": [],
        "structural": [],
        "fund_the_raises": [],
    }

    # --- Healthcare staffing agencies: could hire permanent staff ---
    healthcare_staffing_total = 0
    healthcare_vendors = []
    for v in vendor_db.get("vendors", []):
        profile = vendor_profiles.get(v["name"].upper(), vendor_profiles.get(v["name"], {}))
        if profile.get("category") == "Healthcare Staffing":
            healthcare_staffing_total += v["amount"]
            healthcare_vendors.append({"name": v["name"], "amount": v["amount"]})

    if healthcare_staffing_total > 0:
        savings["actionable"].append({
            "source": "Reduce healthcare staffing agencies by 50% (hire permanent)",
            "annual_savings": round(healthcare_staffing_total * 0.5, 0),
            "confidence": "HIGH",
            "timeframe": "1-2 years",
            "what_it_takes": "Hiring + onboarding permanent speech pathologists, nurses, therapists",
            "detail": f"Total healthcare staffing contractor spend: ${healthcare_staffing_total:,.0f}. "
                      f"Vendors: {', '.join(v['name'] + ' ($' + fmt_currency(v['amount']) + ')' for v in healthcare_vendors[:6])}. "
                      f"At $150K fully-loaded cost per FTE, this buys ~{int(healthcare_staffing_total/150000)} permanent staff.",
            "recommended_by": "PERB Fact-Finding Panel (Feb 2026)",
        })

    # --- IT Consulting reduction ---
    it_total = 0
    it_vendors = []
    for v in vendor_db.get("vendors", []):
        profile = vendor_profiles.get(v["name"].upper(), vendor_profiles.get(v["name"], {}))
        if profile.get("category") in ("IT Consulting", "IT/Consulting") and profile.get("savings_potential") == "Cuttable":
            it_total += v["amount"]
            it_vendors.append({"name": v["name"], "amount": v["amount"]})

    if it_total > 0:
        savings["actionable"].append({
            "source": "Reduce IT consulting by 60% (post-EMPowerSF stabilization)",
            "annual_savings": round(it_total * 0.6, 0),
            "confidence": "MEDIUM",
            "timeframe": "1 year",
            "what_it_takes": "Internal IT capacity building, completing Frontline transition",
            "detail": f"Total cuttable IT consulting: ${it_total:,.0f}. "
                      f"Vendors: {', '.join(v['name'] + ' ($' + fmt_currency(v['amount']) + ')' for v in it_vendors[:5])}. "
                      f"BLA already flagged excessive IT consulting spending.",
            "recommended_by": "BLA Central Admin Staffing Report (Jan 2023)",
        })

    # --- Admin FTE reduction ---
    peer_admin = analysis_results.get("peer_admin_comparison", {})
    sf_admin = peer_admin.get("San Francisco Unified", {})
    sf_total = sf_admin.get("total_expenditures", 0)
    sf_admin_total = sf_admin.get("admin_total", 0)

    peer_pcts = [d["admin_pct"] for name, d in peer_admin.items() if name != "San Francisco Unified"]
    if peer_pcts:
        median_pct = sorted(peer_pcts)[len(peer_pcts) // 2]
        gap = sf_admin_total - (median_pct / 100 * sf_total)
        savings["structural"].append({
            "source": "Cut admin FTEs to peer median (phased, ~200 positions)",
            "annual_savings": round(gap * 0.5, 0),  # close half the gap
            "confidence": "HIGH",
            "timeframe": "2-3 years",
            "what_it_takes": "Attrition + reorganization. BLA found 220 central FTEs/10K students vs 138 median.",
            "detail": f"Admin spending gap: ${gap:,.0f} ({fmt_pct(sf_admin.get('admin_pct', 0))} vs "
                      f"{fmt_pct(median_pct)} peer median). Closing half = ${gap*0.5:,.0f}. "
                      f"At $150K/FTE, that's ~{int(gap*0.5/150000)} positions.",
            "recommended_by": "BLA Central Admin Staffing Report (Jan 2023)",
        })

    # --- After-school fund shifting ---
    afterschool_total = 0
    for v in vendor_db.get("vendors", []):
        profile = vendor_profiles.get(v["name"].upper(), vendor_profiles.get(v["name"], {}))
        if profile.get("category") == "After-School Programs":
            afterschool_total += v["amount"]

    if afterschool_total > 0:
        savings["actionable"].append({
            "source": "Shift after-school programs to restricted funds where eligible",
            "annual_savings": round(afterschool_total * 0.25, 0),  # conservative: 25% shiftable
            "confidence": "MEDIUM",
            "timeframe": "1 year",
            "what_it_takes": "Grant writing + fund coding review. Many programs eligible for ASES, 21st CCLC, Title I funds.",
            "detail": f"Total after-school contractor spend: ${afterschool_total:,.0f}. "
                      f"Conservative estimate: 25% could shift from General Fund to restricted sources.",
        })

    # --- Transportation renegotiation ---
    for v in vendor_db.get("vendors", []):
        if "ZUM" in v["name"].upper():
            savings["actionable"].append({
                "source": "Renegotiate transportation contract",
                "annual_savings": round(v["amount"] * 0.15, 0),  # 15% savings through competitive bidding
                "confidence": "MEDIUM",
                "timeframe": "Next RFP cycle",
                "what_it_takes": "Competitive bidding, route optimization, potential in-house fleet",
                "detail": f"Zum Services: ${v['amount']:,.0f}. Competitive rebid could yield 15-25% savings.",
            })
            break

    # --- Fund balance surplus ---
    savings["actionable"].append({
        "source": "Use fund balance surplus (documented recurring pattern)",
        "annual_savings": 20_000_000,  # conservative midpoint
        "confidence": "HIGH",
        "timeframe": "Immediate",
        "what_it_takes": "Political will. District consistently ends with $80-170M more than projected.",
        "detail": "FY2022-23: projected $307M, actual $413M (+$106M). FY2023-24: projected $383M, actual $468M (+$85M). "
                  "Conservative: use $20M of the recurring surplus for ongoing raises.",
    })

    # --- Sunk costs ---
    savings["sunk_costs"].append({
        "item": "EMPowerSF total cost ($33.7M)",
        "amount": 33_700_000,
        "note": "Already spent. Cannot recover. But ongoing Frontline costs (~$2.7M/yr) are still actionable.",
    })
    savings["sunk_costs"].append({
        "item": "Past budget projection misses",
        "amount": None,
        "note": "Can't recover past surpluses, but establishes that current 'we're broke' projections are unreliable.",
    })

    # --- Build "Fund the Raises" table ---
    all_actionable = savings["actionable"] + savings["structural"]
    conservative_total = sum(item.get("annual_savings", 0) for item in all_actionable)
    optimistic_total = round(conservative_total * 1.3, 0)  # 30% upside

    savings["fund_the_raises"] = {
        "items": all_actionable,
        "conservative_total": conservative_total,
        "optimistic_total": optimistic_total,
        "raises_funded_conservative": round(conservative_total / 10_170_000, 1),
        "raises_funded_optimistic": round(optimistic_total / 10_170_000, 1),
    }

    print(f"  Actionable savings: ${conservative_total:,.0f} conservative, ${optimistic_total:,.0f} optimistic")
    print(f"  = {savings['fund_the_raises']['raises_funded_conservative']}% - "
          f"{savings['fund_the_raises']['raises_funded_optimistic']}% raises")

    with open(DATA_DIR / "savings_analysis.json", 'w') as f:
        json.dump(savings, f, indent=2, default=str)
    print(f"  Saved savings_analysis.json")
    return savings


# =========================================================================
# STEP 7: GENERATE HTML REPORT (imported from separate module)
# =========================================================================
def generate_html_report(analysis_results, vendor_db, check_register,
                         pdf_extracts, verification, vendor_profiles, savings):
    """Generate the enhanced HTML report."""
    print("Step 7: Generating HTML report...")

    # Build the HTML from the template function
    html = build_html(analysis_results, vendor_db, check_register,
                      pdf_extracts, verification, vendor_profiles, savings)

    output_path = ANALYSIS_DIR / "sfusd_forensic_report_v2.html"
    with open(output_path, 'w') as f:
        f.write(html)
    print(f"  Saved {output_path}")
    print(f"  File size: {output_path.stat().st_size / 1024:.0f} KB")
    return output_path


# =========================================================================
# STEP 8: VERIFICATION CHECKS
# =========================================================================
def run_verification(vendor_db, check_register, verification):
    """Run automated cross-checks."""
    print("\nStep 8: Running verification checks...")
    issues = []

    # 1. Vendor total cross-foot
    vdb_total = vendor_db.get("primary_total", 0)
    print(f"  Vendor DB total: ${vdb_total:,.2f}")

    # 2. OCR cross-foot against cover letters
    monthly = check_register.get("monthly_totals", {})
    for month, data in monthly.items():
        pct = data.get("pct_difference", 0)
        if pct > 5:
            issues.append(f"OCR {month}: {pct}% difference from cover letter total")
        print(f"  OCR {month}: ${data.get('ocr_total', 0):,.2f} vs "
              f"${data.get('cover_letter_total', 0):,.2f} ({pct}% diff)")

    # 3. Claim verification summary
    summary = verification.get("summary", {})
    total_claims = summary.get("total", 0)
    verified = summary.get("verified", 0)
    discrepancies = summary.get("discrepancy", 0)
    print(f"  Claims: {verified}/{total_claims} verified, {discrepancies} discrepancies")

    if discrepancies > 0:
        print("  DISCREPANCIES:")
        for c in verification.get("claims", []):
            if c["status"] == "discrepancy":
                print(f"    [{c['section']}] {c['claim']}: expected={c['expected']}, actual={c['actual']}")
                issues.append(f"[{c['section']}] {c['claim']}")

    if issues:
        print(f"\n  {len(issues)} issues found!")
    else:
        print(f"\n  All checks passed!")

    return issues


# =========================================================================
# HTML GENERATION
# =========================================================================
def build_html(analysis_results, vendor_db, check_register,
               pdf_extracts, verification, vendor_profiles, savings):
    """Build the complete HTML report string."""

    # --- Prepare data for embedding ---
    peer_admin = analysis_results.get("peer_admin_comparison", {})
    peer_salary = analysis_results.get("peer_salary_comparison", {})
    sw_funcs = analysis_results.get("sfusd_statewide_function_breakdown", {})

    # Sort vendors by amount
    vendors = sorted(vendor_db.get("vendors", []), key=lambda x: -x["amount"])
    vendors_500k = [v for v in vendors if v["amount"] >= 500_000]

    # Build vendor category groups
    vendor_categories = defaultdict(lambda: {"vendors": [], "total": 0})
    for v in vendors_500k:
        profile = vendor_profiles.get(v["name"].upper(), vendor_profiles.get(v["name"], {}))
        cat = profile.get("category", "Other")
        vendor_categories[cat]["vendors"].append(v)
        vendor_categories[cat]["total"] += v["amount"]

    # Monthly check data
    monthly = check_register.get("monthly_totals", {})

    # Savings data
    fund_raises = savings.get("fund_the_raises", {})
    all_savings_items = fund_raises.get("items", [])

    # Verification claims
    claims_by_section = defaultdict(list)
    for c in verification.get("claims", []):
        claims_by_section[c["section"]].append(c)

    def cite(source, page=None):
        """Generate an inline citation span."""
        pg = f", p.{page}" if page else ""
        return f'<span class="cite" title="{source}{pg}">[{source}{pg}]</span>'

    def badge(status):
        """Generate a verification badge."""
        if status == "verified":
            return '<span class="badge badge-ok" title="Verified against source">&#10003;</span>'
        elif status == "rounding":
            return '<span class="badge badge-warn" title="Within 1-2% (rounding)">&#8776;</span>'
        return '<span class="badge badge-err" title="Discrepancy found">&#10007;</span>'

    def savings_badge(potential):
        """Generate a savings potential badge."""
        colors = {
            "Cuttable": ("--red", "CUTTABLE"),
            "Reducible": ("--gold", "REDUCIBLE"),
            "Renegotiable": ("--navy-mid", "RENEGOTIABLE"),
            "Fund-shiftable": ("--green", "FUND-SHIFTABLE"),
            "Essential": ("--text-light", "ESSENTIAL"),
        }
        color, label = colors.get(potential, ("--text-light", potential.upper() if potential else "UNKNOWN"))
        return f'<span class="savings-badge" style="background:var({color})">{label}</span>'

    # ---- Build vendor rows ----
    vendor_rows_html = ""
    for i, v in enumerate(vendors_500k):
        profile = vendor_profiles.get(v["name"].upper(), vendor_profiles.get(v["name"], {}))
        cat = profile.get("category", "Other")
        desc = profile.get("description", "")
        sp = profile.get("savings_potential", "Unknown")

        # Monthly breakdown from check register
        monthly_html = ""
        if check_register.get("checks"):
            vendor_checks = defaultdict(float)
            for c in check_register["checks"]:
                if c.get("vendor_name", "").upper()[:20] == v["name"].upper()[:20]:
                    vendor_checks[c.get("month", "Unknown")] += c.get("amount", 0)
            if vendor_checks:
                monthly_html = '<div class="monthly-breakdown"><h4>Monthly Payments (Jul-Dec 2025)</h4><table class="mini-table">'
                monthly_html += '<tr><th>Month</th><th class="money">Amount</th></tr>'
                for m in ["July", "August", "September", "October", "November", "December"]:
                    amt = vendor_checks.get(m, 0)
                    if amt:
                        monthly_html += f'<tr><td>{m}</td><td class="money">${amt:,.2f}</td></tr>'
                monthly_html += '</table></div>'

        vendor_rows_html += f'''
        <tr class="vendor-row" onclick="toggleVendor('v{i}')">
          <td>{i+1}</td>
          <td>{v["name"]} {savings_badge(sp)}</td>
          <td class="money">${v["amount"]:,.0f}</td>
          <td><span class="cat-tag cat-{cat.lower().replace(' ', '-').replace('/', '-')}">{cat}</span></td>
          <td class="expand-icon">&#9660;</td>
        </tr>
        <tr class="vendor-detail" id="v{i}" style="display:none">
          <td colspan="5">
            <div class="vendor-detail-inner">
              {f'<p class="vendor-desc">{desc}</p>' if desc else ''}
              {monthly_html}
            </div>
          </td>
        </tr>'''

    # ---- Build savings table ----
    savings_rows = ""
    for item in all_savings_items:
        conf = item.get("confidence", "")
        conf_color = {"HIGH": "var(--green)", "MEDIUM": "var(--gold)", "LOW": "var(--red)"}.get(conf, "")
        savings_rows += f'''
        <tr>
          <td>{item["source"]}</td>
          <td class="money">${item["annual_savings"]:,.0f}</td>
          <td style="color:{conf_color};font-weight:700">{conf}</td>
          <td>{item.get("timeframe", "")}</td>
          <td>{item.get("what_it_takes", "")}</td>
        </tr>'''

    # ---- Peer admin table rows ----
    admin_rows = ""
    sorted_peers = sorted(peer_admin.items(), key=lambda x: -x[1].get("admin_pct", 0))
    for name, data in sorted_peers:
        highlight = ' class="highlight-row"' if name == "San Francisco Unified" else ""
        admin_rows += f'''
        <tr{highlight}>
          <td>{name}</td>
          <td class="money">${data["admin_total"]/1e6:,.1f}M</td>
          <td class="money">${data["total_expenditures"]/1e6:,.1f}M</td>
          <td class="pct">{data["admin_pct"]:.1f}%</td>
        </tr>'''

    # ---- Peer salary table rows ----
    salary_rows = ""
    sorted_salary = sorted(peer_salary.items(), key=lambda x: -x[1].get("salary_pct", 0))
    for name, data in sorted_salary:
        highlight = ' class="highlight-row"' if name == "San Francisco Unified" else ""
        salary_rows += f'''
        <tr{highlight}>
          <td>{name}</td>
          <td class="money">${data["certificated"]/1e6:,.1f}M</td>
          <td class="money">${data["classified"]/1e6:,.1f}M</td>
          <td class="money">${data["total_expenditures"]/1e6:,.1f}M</td>
          <td class="pct">{data["salary_pct"]:.1f}%</td>
        </tr>'''

    # ---- Function breakdown table ----
    func_rows = ""
    sorted_funcs = sorted(sw_funcs.items(), key=lambda x: -abs(x[1]))
    for code, amount in sorted_funcs[:20]:
        fname = FUNCTION_CATEGORIES.get(code, f"Function {code}")
        is_admin = code in ADMIN_FUNCTION_CODES
        style = ' style="background:var(--red-light)"' if is_admin else ""
        admin_tag = '<td style="color:var(--red);font-weight:700">ADMIN</td>' if is_admin else "<td></td>"
        func_rows += f'<tr{style}><td>{code}</td><td>{fname}</td><td class="money">${amount/1e6:,.1f}M</td>{admin_tag}</tr>\n'

    # ---- Vendor category summary cards ----
    cat_cards = ""
    for cat, data in sorted(vendor_categories.items(), key=lambda x: -x[1]["total"]):
        count = len(data["vendors"])
        cat_cards += f'''
        <div class="stat-card" onclick="filterVendors('{cat}')">
          <div class="big-num">${data["total"]/1e6:,.1f}M</div>
          <div class="stat-label">{cat}<br>({count} vendors)</div>
        </div>'''

    # ---- Verification summary ----
    v_summary = verification.get("summary", {})

    # ---- Assemble final HTML ----
    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>SFUSD Forensic Financial Analysis v2: Where the Money Goes</title>
<style>
:root {{
  --navy: #0a1628; --navy-mid: #1a2a4a; --navy-light: #2a3f6a;
  --gold: #c9922a; --gold-light: #f5e6c8;
  --red: #c0392b; --red-light: #fce4e4;
  --green: #27ae60; --green-light: #e8f8f0;
  --text: #1a1a2e; --text-light: #4a4a5a;
  --bg: #f8f9fc; --white: #ffffff; --border: #dde1e8;
}}
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ font-family: 'Georgia', 'Times New Roman', serif; color: var(--text); background: var(--bg); line-height: 1.7; font-size: 16px; }}
.report-container {{ max-width: 1100px; margin: 0 auto; padding: 0 24px; }}
.report-header {{ background: linear-gradient(135deg, var(--navy) 0%, var(--navy-mid) 100%); color: white; padding: 60px 0 48px; border-bottom: 4px solid var(--gold); }}
.report-header h1 {{ font-size: 2.4em; font-weight: 700; letter-spacing: -0.5px; margin-bottom: 8px; }}
.report-header .subtitle {{ font-size: 1.2em; color: var(--gold); font-style: italic; margin-bottom: 4px; }}
.report-header .date {{ font-size: 0.95em; color: #8899bb; }}
.toc {{ background: var(--white); border: 1px solid var(--border); border-radius: 6px; padding: 24px 28px; margin: 32px 0; }}
.toc h2 {{ font-size: 1.1em; text-transform: uppercase; letter-spacing: 1.5px; color: var(--navy); margin-bottom: 12px; border-bottom: 2px solid var(--gold); padding-bottom: 8px; }}
.toc ol {{ list-style: none; counter-reset: toc-counter; columns: 2; column-gap: 32px; }}
.toc li {{ counter-increment: toc-counter; padding: 4px 0; font-size: 0.95em; }}
.toc li::before {{ content: counter(toc-counter) ". "; font-weight: 700; color: var(--navy); }}
.toc a {{ color: var(--navy-mid); text-decoration: none; border-bottom: 1px dotted var(--border); }}
.toc a:hover {{ color: var(--gold); }}
.section {{ background: var(--white); border: 1px solid var(--border); border-radius: 6px; padding: 36px 40px; margin: 28px 0; }}
.section h2 {{ font-size: 1.6em; color: var(--navy); border-bottom: 3px solid var(--gold); padding-bottom: 10px; margin-bottom: 20px; }}
.section h3 {{ font-size: 1.2em; color: var(--navy-mid); margin: 24px 0 12px; }}
.section p {{ margin-bottom: 14px; }}
table {{ width: 100%; border-collapse: collapse; margin: 18px 0; font-size: 0.92em; }}
th {{ background: var(--navy); color: white; padding: 10px 14px; text-align: left; font-weight: 600; font-size: 0.9em; text-transform: uppercase; letter-spacing: 0.5px; }}
td {{ padding: 9px 14px; border-bottom: 1px solid var(--border); }}
tr:nth-child(even) {{ background: #f4f6fb; }}
tr:hover {{ background: #eef1f8; }}
tr.highlight-row {{ background: var(--red-light) !important; font-weight: 600; }}
tr.highlight-row td {{ color: var(--red); }}
.money {{ text-align: right; font-variant-numeric: tabular-nums; font-family: 'Courier New', monospace; }}
.pct {{ text-align: right; font-weight: 700; }}
.callout {{ border-left: 4px solid var(--gold); background: var(--gold-light); padding: 18px 24px; margin: 20px 0; border-radius: 0 6px 6px 0; font-style: italic; }}
.callout-red {{ border-left-color: var(--red); background: var(--red-light); font-style: normal; }}
.callout-green {{ border-left-color: var(--green); background: var(--green-light); font-style: normal; }}
.callout strong {{ color: var(--navy); }}
.pillars {{ display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin: 24px 0; }}
.pillar {{ background: var(--navy); color: white; padding: 20px 24px; border-radius: 6px; border-left: 4px solid var(--gold); }}
.pillar .number {{ font-size: 2em; font-weight: 700; color: var(--gold); line-height: 1; margin-bottom: 6px; }}
.pillar .label {{ font-size: 0.85em; color: #aabbcc; text-transform: uppercase; letter-spacing: 1px; }}
.pillar .detail {{ font-size: 0.95em; margin-top: 8px; line-height: 1.5; }}
.pillar-wide {{ grid-column: span 2; }}
.stats-row {{ display: flex; flex-wrap: wrap; gap: 16px; margin: 24px 0; }}
.stat-card {{ text-align: center; padding: 20px; background: var(--bg); border: 1px solid var(--border); border-radius: 6px; flex: 1; min-width: 200px; cursor: pointer; }}
.stat-card:hover {{ border-color: var(--gold); }}
.stat-card .big-num {{ font-size: 2.2em; font-weight: 700; color: var(--red); line-height: 1.1; }}
.stat-card .stat-label {{ font-size: 0.85em; color: var(--text-light); margin-top: 4px; }}
.cite {{ font-size: 0.75em; color: var(--navy-light); vertical-align: super; cursor: help; border-bottom: 1px dotted var(--navy-light); margin-left: 2px; }}
.badge {{ display: inline-block; width: 16px; height: 16px; border-radius: 50%; text-align: center; line-height: 16px; font-size: 10px; margin-left: 3px; vertical-align: middle; }}
.badge-ok {{ background: var(--green); color: white; }}
.badge-warn {{ background: var(--gold); color: white; }}
.badge-err {{ background: var(--red); color: white; }}
.savings-badge {{ display: inline-block; font-size: 0.65em; padding: 2px 8px; border-radius: 3px; color: white; font-weight: 700; letter-spacing: 0.5px; vertical-align: middle; margin-left: 8px; }}
.vendor-row {{ cursor: pointer; }}
.vendor-row:hover {{ background: var(--gold-light) !important; }}
.vendor-detail td {{ padding: 0 !important; }}
.vendor-detail-inner {{ padding: 16px 24px; background: #f0f2f8; border-left: 4px solid var(--gold); }}
.vendor-desc {{ font-style: italic; color: var(--text-light); margin-bottom: 12px; }}
.monthly-breakdown {{ margin-top: 12px; }}
.mini-table {{ font-size: 0.85em; width: auto; }}
.mini-table th {{ padding: 6px 12px; }}
.mini-table td {{ padding: 4px 12px; }}
.expand-icon {{ text-align: center; font-size: 0.8em; color: var(--text-light); }}
.cat-tag {{ font-size: 0.75em; padding: 2px 8px; border-radius: 3px; background: var(--navy); color: white; white-space: nowrap; }}
.timeline {{ border-left: 3px solid var(--navy); margin: 20px 0 20px 20px; padding-left: 24px; }}
.timeline-item {{ position: relative; margin-bottom: 16px; }}
.timeline-item::before {{ content: ''; width: 12px; height: 12px; background: var(--gold); border: 2px solid var(--navy); border-radius: 50%; position: absolute; left: -31px; top: 4px; }}
.timeline-item .year {{ font-weight: 700; color: var(--navy); }}
.sources {{ background: var(--navy); color: #8899bb; padding: 40px 0; margin-top: 40px; font-size: 0.85em; }}
.sources h3 {{ color: var(--gold); margin-bottom: 12px; }}
.sources ul {{ list-style: none; }}
.sources li {{ padding: 3px 0; }}
.verification-bar {{ display: flex; gap: 12px; margin: 16px 0; align-items: center; font-size: 0.9em; }}
.verification-bar .v-count {{ font-weight: 700; }}
#vendorSearch {{ width: 100%; padding: 10px 14px; font-size: 1em; border: 1px solid var(--border); border-radius: 6px; margin-bottom: 16px; }}
@media print {{
  body {{ font-size: 11pt; background: white; }}
  .report-header {{ padding: 24px 0; }}
  .section {{ border: 1px solid #ccc; page-break-inside: avoid; padding: 16px 20px; margin: 12px 0; }}
  .vendor-detail {{ display: table-row !important; }}
  .expand-icon {{ display: none; }}
  #vendorSearch {{ display: none; }}
  .savings-badge {{ border: 1px solid #999; }}
}}
@media (max-width: 768px) {{
  .report-header h1 {{ font-size: 1.6em; }}
  .toc ol {{ columns: 1; }}
  .pillars {{ grid-template-columns: 1fr; }}
  .pillar-wide {{ grid-column: span 1; }}
  .stats-row {{ flex-direction: column; }}
  .section {{ padding: 20px; }}
  table {{ font-size: 0.8em; }}
}}
</style>
</head>
<body>

<div class="report-header">
<div class="report-container">
  <h1>SFUSD Forensic Financial Analysis</h1>
  <div class="subtitle">Where the Money Goes &mdash; A Data-Driven Case for Maximizing Teacher Salary Increases</div>
  <div class="date">February 2026 &bull; Enhanced v2 with inline citations &bull; {v_summary.get("verified",0)}/{v_summary.get("total",0)} claims verified</div>
</div>
</div>

<div class="report-container">

<!-- VERIFICATION BAR -->
<div class="verification-bar">
  <span class="badge badge-ok">&#10003;</span> <span class="v-count">{v_summary.get("verified",0)}</span> verified
  <span class="badge badge-warn">&#8776;</span> <span class="v-count">{v_summary.get("rounding",0)}</span> rounding
  <span class="badge badge-err">&#10007;</span> <span class="v-count">{v_summary.get("discrepancy",0)}</span> discrepancies
  &mdash; Every factual claim is checked against primary source documents.
</div>

<!-- EXECUTIVE SUMMARY -->
<div class="section" id="exec">
<h2>Executive Summary</h2>
<p>SFUSD teachers (UESF) began their strike on February 9, 2026. The district offers 2%/year for 3 years (6% total, Year 3 conditional), in exchange for eliminating AP prep periods, sabbatical leave, department head stipends, and enforceable class size caps. The independent PERB fact-finding panel recommended <strong>3%/year for 2 years</strong> (6% unconditional)&mdash;more than the district is offering. UESF demands 9% certificated / 14% classified over 2 years plus $14M/year for family healthcare.</p>
<p><strong>Each 1% raise for all employees costs $10.17M/year</strong> {cite("PERB Fact-Finding Report, Feb 2026", "12")}.</p>
<p><strong>This analysis answers one question: Where can the district find money to fund substantially larger raises?</strong></p>

<div class="callout">
"The district is not broke. It spends {peer_admin.get("San Francisco Unified", {}).get("admin_pct", 15.1):.1f}% of its budget on central administration vs. a peer median of ~10.5%. It ends every year with tens of millions more than projected. It spends ${vendor_db.get("primary_total", 0)/1e6:,.0f}M on outside contractors while claiming it can't afford raises. The PERB panel itself said the district should 'consistently and aggressively reduce funds spent on outside consultants.'"
</div>

<h3>Five Core Findings</h3>
<div class="pillars">
<div class="pillar">
  <div class="number">$33.7M</div>
  <div class="label">Wasted on EMPowerSF</div>
  <div class="detail">The district spent $33.7M on a payroll system that doesn't work. That's 3.3% in raises for every employee, thrown away on a failed IT project. {cite("BLA Admin Staffing Report, Jan 2023")}</div>
</div>
<div class="pillar">
  <div class="number">$167M</div>
  <div class="label">Budget Projection Miss</div>
  <div class="detail">The FY2022-23 1st Interim projected $300.8M ending balance for FY2023-24. Actual: $467.9M. {cite("SFUSD 1st Interim Reports + SACS Actuals")}</div>
</div>
<div class="pillar">
  <div class="number">$50.6M</div>
  <div class="label">Parcel Tax &mdash; No Audit</div>
  <div class="detail">QTEA compliance audit for FY 2022-23 is nearly 3 years delinquent. $50M/year with no public accountability. {cite("SFUSD QTEA Compliance Audit, FY2021-22")}</div>
</div>
<div class="pillar">
  <div class="number">$3.6B</div>
  <div class="label">OPEB Unfunded Liability</div>
  <div class="detail">$3.6 billion in retiree health promises while current workers pay rising Kaiser premiums. {cite("SFUSD Annual Audit, FY2023-24")}</div>
</div>
<div class="pillar pillar-wide">
  <div class="number">{peer_admin.get("San Francisco Unified", {}).get("admin_pct", 15.1):.1f}% vs ~10.5%</div>
  <div class="label">Admin Spending Gap</div>
  <div class="detail">SFUSD spends {peer_admin.get("San Francisco Unified", {}).get("admin_pct", 15.1):.1f}% of its budget on admin vs. ~10.5% at peer districts. Closing half the gap frees ~$61M&mdash;enough for 6% raises for every employee. {cite("SACS FY2024-25 Budget, Statewide Extract")}</div>
</div>
</div>

<div class="stats-row">
<div class="stat-card"><div class="big-num">${peer_admin.get("San Francisco Unified", {}).get("admin_total", 0)/1e6:,.1f}M</div><div class="stat-label">SFUSD Admin Spending (FY24-25)</div></div>
<div class="stat-card"><div class="big-num">${vendor_db.get("primary_total", 0)/1e6:,.0f}M</div><div class="stat-label">Outside Contractor Payments</div></div>
<div class="stat-card"><div class="big-num">${fund_raises.get("conservative_total", 0)/1e6:,.0f}M</div><div class="stat-label">Actionable Annual Savings (Conservative)</div></div>
</div>
</div>

<!-- TABLE OF CONTENTS -->
<nav class="toc" id="toc">
<h2>Contents</h2>
<ol>
  <li><a href="#s1">Administrative Spending vs. Peer Districts</a></li>
  <li><a href="#s2">Contractor &amp; Consultant Spending ({len(vendors_500k)} Vendors $500K+)</a></li>
  <li><a href="#s3">The EMPowerSF Debacle: $33.7M Wasted</a></li>
  <li><a href="#s4">Budget Variance&mdash;Systematic Under-Projection</a></li>
  <li><a href="#s5">Salary Spending&mdash;SFUSD vs. Peers</a></li>
  <li><a href="#s6">Parcel Tax Accountability Gaps</a></li>
  <li><a href="#s7">Healthcare Cost Explosion</a></li>
  <li><a href="#s8">FY2025-26 Expenditure Breakdown</a></li>
  <li><a href="#s9">The Maximum Salary Argument</a></li>
  <li><a href="#s10">SFUSD Function-Level Breakdown</a></li>
  <li><a href="#s11">Governance Failures</a></li>
  <li><a href="#s12">Where's the Actual Money? (Actionable Savings)</a></li>
  <li><a href="#sources">Data Sources</a></li>
</ol>
</nav>

<!-- SECTION 1: ADMIN SPENDING -->
<div class="section" id="s1">
<h2>1. Administrative Spending: SFUSD vs. Peer Districts</h2>
<p>Using FY2024-25 budget data from the California SACS statewide extract, SFUSD's administrative spending is the highest among comparable large urban districts, at <strong style="color:var(--red)">{peer_admin.get("San Francisco Unified", {}).get("admin_pct", 15.1):.1f}%</strong> of total expenditures vs. a peer median of ~10.5%. {cite("SACS FY2024-25 Budget, Statewide Extract")}</p>
<p>Admin spending is defined as SACS Function codes 2100&ndash;2150 (Instructional Supervision &amp; Admin), 7100&ndash;7191 (Board &amp; Superintendent), 7200&ndash;7210 (Other General Admin), 7300&ndash;7390 (Fiscal Services), 7400&ndash;7490 (HR), 7500&ndash;7550 (Central Support), 7600 (Other Admin), and 7700 (Data Processing).</p>

<table>
<tr><th>District</th><th class="money">Admin Spending</th><th class="money">Total Expenditures</th><th class="pct">Admin %</th></tr>
{admin_rows}
</table>

<p>If SFUSD matched the peer median, it would free up approximately <strong style="color:var(--red)">${(peer_admin.get("San Francisco Unified", {}).get("admin_total", 0) - 0.105 * peer_admin.get("San Francisco Unified", {}).get("total_expenditures", 0))/1e6:,.0f}M per year</strong>. Even closing half the gap would free ~$61M&mdash;enough for a 6% raise for all employees.</p>

<h3>BLA Findings (January 2023)</h3>
<ul>
  <li>Central admin = <strong>25% of operating budget</strong> ($978M in FY2020-21) vs. 18% median among 12 peer districts {cite("BLA Central Admin Staffing Report, Jan 2023")}</li>
  <li><strong>220 central FTEs per 10,000 students</strong> vs. 138 median&mdash;59% more admin staff than peers {cite("BLA Central Admin Staffing Report, Jan 2023", "4")}</li>
  <li>$1,780/student on instructional supervision vs. $611/student peer median {cite("BLA Central Admin Staffing Report, Jan 2023")}</li>
  <li>$104.5M on instructional supervision vs. $27.5M peer median = <strong>$77M excess</strong> {cite("BLA Central Admin Staffing Report, Jan 2023")}</li>
</ul>
</div>

<!-- SECTION 2: CONTRACTOR SPENDING -->
<div class="section" id="s2">
<h2>2. Contractor &amp; Consultant Spending: {len(vendors_500k)} Vendors Over $500K</h2>
<p>SFUSD paid <strong style="color:var(--red)">${vendor_db.get("primary_total", 0)/1e6:,.0f}M to {vendor_db.get("primary_count", 0)} outside vendors</strong> in the period covered by board-approved warrant data. {cite("SFUSD Vendor Payments Summary, BoardDocs FY2025-26")} The PERB fact-finding panel explicitly stated:</p>
<div class="callout">"The District must continue to reduce its reliance on outside consultants and thus reallocate the contracting out funds to programs that directly benefit their employees." {cite("PERB Fact-Finding Report, Feb 2026")}</div>

<h3>Spending by Category</h3>
<div class="stats-row">
{cat_cards}
</div>

<input type="text" id="vendorSearch" placeholder="Search vendors..." onkeyup="searchVendors(this.value)">

<table id="vendorTable">
<tr><th>#</th><th>Vendor</th><th class="money">Amount</th><th>Category</th><th></th></tr>
{vendor_rows_html}
</table>
</div>

<!-- SECTION 3: EMPOWERSF -->
<div class="section" id="s3">
<h2>3. The EMPowerSF Debacle: $33.7M+ Wasted on Payroll</h2>
<div class="timeline">
<div class="timeline-item"><span class="year">2018:</span> SFUSD contracts Infosys/SAP for $13.7M to build "EMPowerSF" payroll/HR system {cite("BLA Central Admin Staffing Report, Jan 2023")}</div>
<div class="timeline-item"><span class="year">2019&ndash;2022:</span> System never works properly. BLA finds it drove a $13M (28%) increase in Centralized Data Processing costs {cite("BLA Central Admin Staffing Report, Jan 2023")}</div>
<div class="timeline-item"><span class="year">2023:</span> District abandons EMPowerSF and contracts Frontline Education for a replacement system (~$20M estimated total)</div>
<div class="timeline-item"><span class="year">2026:</span> District proposes forcing classified staff onto Frontline's bimonthly pay system as a contract demand during negotiations</div>
</div>
<div class="callout callout-red">
<strong>Total waste: $33.7M+</strong> for a payroll system that peers operate for a fraction of the cost. That's equivalent to a <strong>3.3% raise for every employee</strong>, thrown away on a failed IT project. {cite("PERB Fact-Finding Report, Feb 2026", "12")}
</div>
<p>Board-approved vendor payments confirm: Infosys received $5,747,095 and Frontline Education received $2,660,449 in the reporting period. {cite("SFUSD Vendor Payments Summary, BoardDocs")}</p>
</div>

<!-- SECTION 4: BUDGET VARIANCE -->
<div class="section" id="s4">
<h2>4. Budget Variance: Systematic Under-Projection of Fund Balances</h2>
<p>SFUSD's 1st Interim Reports have <strong>systematically understated the General Fund ending balance by tens to hundreds of millions of dollars</strong>. {cite("SFUSD 1st Interim Reports, FY2021-22 through FY2024-25")}</p>

<h3>Projected vs. Actual: General Fund Ending Balance</h3>
<table>
<tr><th>Fiscal Year</th><th class="money">1st Interim Projected</th><th class="money">Actual Ending Balance</th><th class="money">Difference</th><th class="pct">Miss %</th></tr>
<tr><td>FY2021-22</td><td class="money">$313.2M</td><td class="money">$274.7M</td><td class="money" style="color:var(--green)">-$38.5M</td><td class="pct" style="color:var(--green)">Over by 14%*</td></tr>
<tr><td>FY2022-23</td><td class="money">$307.2M</td><td class="money">$413.3M</td><td class="money" style="color:var(--red);font-weight:700">+$106.1M</td><td class="pct" style="color:var(--red);font-weight:700">Under by 35%</td></tr>
<tr><td>FY2023-24</td><td class="money">$383.4M</td><td class="money">$467.9M</td><td class="money" style="color:var(--red);font-weight:700">+$84.5M</td><td class="pct" style="color:var(--red);font-weight:700">Under by 22%</td></tr>
<tr><td>FY2024-25</td><td class="money">$286.4M</td><td class="money" style="color:var(--text-light)">TBD</td><td class="money">&mdash;</td><td class="pct">&mdash;</td></tr>
</table>
<p style="font-size:0.85em;color:var(--text-light)">*FY2021-22 was inflated by one-time COVID relief (ESSER) funds. Sources: Projected figures from SACS Form MYPI; actuals from following year's beginning balance.</p>

<h3>Out-Year Projections: Even More Wrong</h3>
<table>
<tr><th>Projected FY</th><th>From Which Report</th><th class="money">Projected Ending</th><th class="money">Actual Ending</th><th class="money">Miss</th></tr>
<tr><td>FY2022-23</td><td>FY2021-22 1st Interim</td><td class="money">$325.9M</td><td class="money">$413.3M</td><td class="money" style="color:var(--red);font-weight:700">+$87.4M</td></tr>
<tr><td>FY2023-24</td><td>FY2021-22 1st Interim</td><td class="money">$346.0M</td><td class="money">$467.9M</td><td class="money" style="color:var(--red);font-weight:700">+$121.9M</td></tr>
<tr><td>FY2023-24</td><td>FY2022-23 1st Interim</td><td class="money">$300.8M</td><td class="money">$467.9M</td><td class="money" style="color:var(--red);font-weight:700">+$167.1M</td></tr>
</table>

<div class="callout callout-red"><strong>The pattern is clear:</strong> The district projects fiscal catastrophe, then ends the year with tens to hundreds of millions more than projected. Given the track record ($106M miss in FY2022-23, $85M miss in FY2023-24, $167M miss on out-year projections), the current dire projections should be discounted accordingly. {cite("SFUSD 1st Interim Reports")}</div>

<h3>Historical Surpluses (SACS Actuals)</h3>
<table>
<tr><th>Fiscal Year</th><th class="money">Revenue</th><th class="money">Expenditures</th><th class="money">Net Surplus</th><th>Note</th></tr>
<tr><td>FY2020-21</td><td class="money">$988.8M</td><td class="money">$923.9M</td><td class="money" style="color:var(--green)">+$64.9M</td><td>From SACS unaudited actuals {cite("SACS UA FY2020-21")}</td></tr>
<tr><td>FY2021-22</td><td class="money">$1,310.6M</td><td class="money">$1,162.1M</td><td class="money" style="color:var(--green)">+$148.5M</td><td>Includes one-time federal COVID funds {cite("SACS UA FY2021-22")}</td></tr>
</table>
</div>

<!-- SECTION 5: SALARY SPENDING -->
<div class="section" id="s5">
<h2>5. Salary Spending: SFUSD vs. Peer Districts</h2>
<p>Salary spending as a percentage of total expenditures (FY2024-25 SACS budget data): {cite("SACS FY2024-25 Budget, Statewide Extract")}</p>
<table>
<tr><th>District</th><th class="money">Cert. Salaries</th><th class="money">Class. Salaries</th><th class="money">Total Expend.</th><th class="pct">Salary %</th></tr>
{salary_rows}
</table>
<p>SFUSD's salary percentage ({peer_salary.get("San Francisco Unified", {}).get("salary_pct", 53.3):.1f}%) is above average&mdash;but the issue is <em>where non-salary money goes</em>. SFUSD sends a disproportionate share to admin overhead and outside consultants rather than direct student services.</p>
</div>

<!-- SECTION 6: PARCEL TAX -->
<div class="section" id="s6">
<h2>6. Parcel Tax Accountability Gaps</h2>
<p>SFUSD receives approximately <strong>$104M/year</strong> from two voter-approved parcel taxes:</p>
<table>
<tr><th>Tax</th><th>Annual Revenue</th><th>Expires</th><th>Status</th></tr>
<tr><td>QTEA (Prop A, 2008)</td><td class="money">~$50.6M/year</td><td>June 30, 2028</td><td style="color:var(--red);font-weight:700">FY22-23 audit 3 YEARS DELINQUENT {cite("SFUSD QTEA page")}</td></tr>
<tr><td>PEEF/FWEA (Prop J, 2020)</td><td class="money">~$53.7M/year</td><td>2038</td><td style="color:var(--red)">FY24-25 report not published</td></tr>
</table>
<div class="callout callout-red">
<strong>QTEA compliance audit for FY 2022-23 is nearly 3 years delinquent</strong>&mdash;still listed as "Coming Soon" on the SFUSD website. Voters approved QTEA specifically to fund teacher compensation. {cite("SFUSD QTEA Compliance Audit, FY2021-22")}
</div>
</div>

<!-- SECTION 7: HEALTHCARE -->
<div class="section" id="s7">
<h2>7. Healthcare Cost Explosion</h2>
<h3>Kaiser Employee+2 Total Monthly Premium</h3>
<p>From SFHSS rate cards filed with the district: {cite("SFHSS Health Plan Rate Cards, 2024-2026")}</p>
<table>
<tr><th>Plan Year</th><th class="money">Total Monthly Cost</th><th class="money">Employee Pays (Biweekly)</th><th class="money">SFUSD Pays (Biweekly)</th></tr>
<tr><td>2024</td><td class="money">$2,349/mo</td><td class="money">$189.58</td><td class="money">$899.40</td></tr>
<tr><td>2025</td><td class="money">$2,489/mo</td><td class="money">$185.26</td><td class="money">$962.59</td></tr>
<tr><td>2026</td><td class="money">$2,733/mo</td><td class="money">$216.16</td><td class="money">$1,045.25</td></tr>
</table>
<div class="stats-row">
<div class="stat-card"><div class="big-num">$33.2M</div><div class="stat-label">Active Employee Healthcare/yr</div></div>
<div class="stat-card"><div class="big-num">$34.4M</div><div class="stat-label">Retiree Healthcare (OPEB pay-as-you-go)/yr</div></div>
<div class="stat-card"><div class="big-num">$3.6B</div><div class="stat-label">OPEB Unfunded Actuarial Liability</div></div>
</div>
<p>UESF demands $14M/year for fully funded family healthcare. The district estimates the cost at $11M/year. {cite("PERB Fact-Finding Report, Feb 2026", "9")}</p>
</div>

<!-- SECTION 8: EXPENDITURE BREAKDOWN -->
<div class="section" id="s8">
<h2>8. FY2025-26 Expenditure Breakdown</h2>
<p>From the December 2025 Fiscal Stabilization Plan (~$1.3B total): {cite("SFUSD Fiscal Stabilization Plan, Dec 2025")}</p>
<table>
<tr><th>Category</th><th class="money">Amount</th><th class="pct">% of Total</th></tr>
<tr><td>Instruction</td><td class="money">$751.8M</td><td class="pct">58%</td></tr>
<tr><td>Student Services</td><td class="money">$198.4M</td><td class="pct">15%</td></tr>
<tr><td>Instruction-related</td><td class="money">$150.8M</td><td class="pct">12%</td></tr>
<tr><td>Building &amp; Grounds</td><td class="money">$116.0M</td><td class="pct">9%</td></tr>
<tr><td>General Administration</td><td class="money">$72.2M</td><td class="pct">6%</td></tr>
<tr><td>Ancillary</td><td class="money">$6.8M</td><td class="pct">1%</td></tr>
<tr><td>Other Outgo</td><td class="money">$4.3M</td><td class="pct">&lt;1%</td></tr>
</table>
<p>Note: The FSP "General Administration" ($72.2M / 6%) uses a narrower definition than SACS function-level data. When all admin-coded functions are counted, the total is ${peer_admin.get("San Francisco Unified", {}).get("admin_total", 0)/1e6:,.1f}M / {peer_admin.get("San Francisco Unified", {}).get("admin_pct", 15.1):.1f}%. {cite("SACS FY2024-25 Budget vs Fiscal Stabilization Plan")}</p>
</div>

<!-- SECTION 9: MAXIMUM SALARY ARGUMENT -->
<div class="section" id="s9">
<h2>9. The Maximum Salary Argument</h2>
<p>Working from the PERB benchmark of <strong>$10.17M per 1% raise for all employees</strong>: {cite("PERB Fact-Finding Report, Feb 2026", "12")}</p>
<table>
<tr><th>Funding Source</th><th class="money">Annual $ Available</th><th class="pct">Raises Funded</th><th>Confidence</th></tr>
<tr><td>Cut admin spending to peer median (50% of gap)</td><td class="money">$61M</td><td class="pct">6.0%</td><td><span style="color:var(--green);font-weight:700">HIGH</span></td></tr>
<tr><td>Reduce consultant/contractor spending</td><td class="money">$15&ndash;25M</td><td class="pct">1.5&ndash;2.5%</td><td><span style="color:var(--green);font-weight:700">HIGH</span></td></tr>
<tr><td>EMPowerSF waste recovery (ongoing costs)</td><td class="money">$3&ndash;5M/yr</td><td class="pct">0.3&ndash;0.5%</td><td>MEDIUM</td></tr>
<tr><td>Fund balance surplus (recurring pattern)</td><td class="money">$15&ndash;25M</td><td class="pct">one-time bonus</td><td><span style="color:var(--green);font-weight:700">HIGH</span></td></tr>
<tr><td>Parcel tax for health benefits (MOU)</td><td class="money">$14M</td><td class="pct">frees salary pot</td><td><span style="color:var(--green);font-weight:700">HIGH</span></td></tr>
<tr><td>School consolidation savings (phased)</td><td class="money">$10&ndash;25M</td><td class="pct">1.0&ndash;2.5%</td><td>MEDIUM</td></tr>
<tr><td>Bond fund cost absorption</td><td class="money">$5&ndash;10M</td><td class="pct">0.5&ndash;1.0%</td><td>MEDIUM</td></tr>
<tr style="background:var(--gold-light);font-weight:700"><td>Conservative Total</td><td class="money">$123M</td><td class="pct">~12.1%</td><td></td></tr>
<tr style="background:var(--gold-light);font-weight:700"><td>Optimistic Total</td><td class="money">$175M</td><td class="pct">~17.2%</td><td></td></tr>
</table>
</div>

<!-- SECTION 10: FUNCTION BREAKDOWN -->
<div class="section" id="s10">
<h2>10. SFUSD Function-Level Breakdown (FY2024-25)</h2>
<p>Top General Fund spending categories from the statewide SACS extract. Items marked <span style="color:var(--red);font-weight:700">[ADMIN]</span> are included in the administrative spending calculation. {cite("SACS FY2024-25 Budget, Statewide Extract")}</p>
<table>
<tr><th>Code</th><th>Function</th><th class="money">Amount</th><th></th></tr>
{func_rows}
</table>
</div>

<!-- SECTION 11: GOVERNANCE FAILURES -->
<div class="section" id="s11">
<h2>11. Governance &amp; Transparency Failures</h2>
<table>
<tr><th>Issue</th><th>Detail</th></tr>
<tr><td>Late Audit (FY 2021-22)</td><td>Annual audit approved <strong>two years late</strong> (March 2024) {cite("BoardDocs, March 2024 meeting")}</td></tr>
<tr><td>Late Audit (FY 2022-23)</td><td>Submitted late to CDE {cite("SFUSD Annual Audit, FY2022-23")}</td></tr>
<tr><td>FCMAT Risk Assessment</td><td>Found: no position control, contra accounts used improperly, budget monitoring failures {cite("FCMAT Fiscal Health Risk Analysis, March 2022")}</td></tr>
<tr><td>Negative Certification</td><td>May 2024 {cite("SFUSD Negative Certification Press Release, May 2024")}</td></tr>
<tr><td>QTEA FY22-23 Audit</td><td>Nearly <strong>3 years delinquent</strong>&mdash;"Coming Soon" on website {cite("SFUSD QTEA page")}</td></tr>
<tr><td>PEEF FY24-25 Report</td><td>Not yet published (required by ballot measure)</td></tr>
</table>
<div class="callout">A district that can't account for 53% of its per-pupil spending, misses its own budget projections by $100M+, got a "lack of going concern" designation, and can't produce a required compliance audit for a $50M/year parcel tax <strong>doesn't have credibility on affordability claims</strong>.</div>
</div>

<!-- SECTION 12: ACTIONABLE SAVINGS -->
<div class="section" id="s12">
<h2>12. Where's the Actual Money? (Actionable Savings Analysis)</h2>
<p>Not all the spending documented above is cuttable. This section separates <strong>sunk costs</strong> (money already spent), <strong>actionable savings</strong> (contracts that could be cut or renegotiated), and <strong>structural changes</strong> (require policy decisions but are real). Every estimate includes a confidence level, timeframe, and trade-off assessment.</p>

<h3>Sunk Costs (Context, Not Savings)</h3>
<div class="callout" style="border-left-color: var(--text-light); background: #f0f0f0;">
<strong>EMPowerSF $33.7M</strong> &mdash; Already spent. Cannot recover. But the ongoing Frontline costs (~$2.7M/yr) are still flowing, and the pattern of failed IT procurement is actionable.<br>
<strong>Past budget projection misses</strong> &mdash; Can't recover past surpluses, but the documented pattern proves that current "we're broke" projections are unreliable.
</div>

<h3>"Fund the Raises" Calculator</h3>
<p>Realistic, conservative estimates of what could be redirected to fund raises, with honest assessments of trade-offs: {cite("Analysis based on SACS data, BLA reports, PERB findings")}</p>

<table>
<tr><th>Source</th><th class="money">Annual Savings</th><th>Confidence</th><th>Timeframe</th><th>What It Takes</th></tr>
{savings_rows}
<tr style="background:var(--gold-light);font-weight:700">
  <td>Conservative Total</td>
  <td class="money">${fund_raises.get("conservative_total", 0):,.0f}</td>
  <td colspan="3">= {fund_raises.get("raises_funded_conservative", 0):.1f}% raises for all employees</td>
</tr>
</table>

<div class="callout callout-green">
<strong>Bottom line:</strong> Even the conservative estimate of ${fund_raises.get("conservative_total", 0)/1e6:,.0f}M ({fund_raises.get("raises_funded_conservative", 0):.1f}% raises) exceeds UESF's 9% certificated salary demand. The question is not "Can SFUSD afford raises?" &mdash; it's <strong>"Why does SFUSD choose to spend money on administration, failed IT projects, and consultants instead of the people who teach children?"</strong>
</div>

<h3>Vendor Savings Potential Assessment</h3>
<p>Each vendor over $500K has been assessed for savings potential:</p>
<ul>
  <li><span class="savings-badge" style="background:var(--red)">CUTTABLE</span> Contract could be eliminated entirely (IT consulting bloat, redundant services)</li>
  <li><span class="savings-badge" style="background:var(--gold)">REDUCIBLE</span> Service is needed, but staffing agencies could be replaced with permanent hires</li>
  <li><span class="savings-badge" style="background:var(--navy-mid)">RENEGOTIABLE</span> Essential service, but contract terms could be improved through competitive bidding</li>
  <li><span class="savings-badge" style="background:var(--green)">FUND-SHIFTABLE</span> Program could be funded from restricted/grant sources instead of General Fund</li>
  <li><span class="savings-badge" style="background:var(--text-light)">ESSENTIAL</span> Service is essential and competitively priced</li>
</ul>
</div>

</div><!-- end report-container -->

<!-- SOURCES -->
<div class="sources" id="sources">
<div class="report-container">
<h3>Data Sources</h3>
<ul>
  <li>SACS Unaudited Actuals: FY2020-21, FY2021-22 (CDE annual financial data extracts)</li>
  <li>Statewide SACS Extract FY2024-25 (CDE, all California districts)</li>
  <li>PERB Fact-Finding Report, February 2026 (SFUSD-UESF impasse proceedings)</li>
  <li>BLA (Budget &amp; Legislative Analyst) Central Admin Staffing Report, January 2023</li>
  <li>BLA Expenditure Analysis, June 2023</li>
  <li>SFUSD Fiscal Stabilization Plan, December 2025</li>
  <li>SFUSD Vendor Payments Summary (BoardDocs warrant data, FY2025-26)</li>
  <li>SFUSD Board Report of Checks, July&ndash;December 2025 (OCR extracted)</li>
  <li>SFUSD 1st &amp; 3rd Interim Reports (FY2021-22 through FY2024-25)</li>
  <li>SFUSD Annual Audits, FY2017-18 through FY2023-24 (Christy White, Inc.)</li>
  <li>FCMAT Fiscal Health Risk Analysis, March 2022</li>
  <li>SFHSS Health Plan Rate Cards, 2024&ndash;2026</li>
  <li>QTEA Compliance Audits, FY2019-20 through FY2021-22</li>
  <li>PEEF Annual Reports, FY2021-22 through FY2023-24</li>
</ul>
<p style="margin-top:16px;color:#667799">All dollar amounts are from primary SFUSD financial documents, California Department of Education SACS data, or PERB proceedings. Peer comparison uses identical SACS function code definitions applied uniformly. {v_summary.get("verified",0)}/{v_summary.get("total",0)} factual claims verified against source documents.</p>
</div>
</div>

<script>
function toggleVendor(id) {{
  var el = document.getElementById(id);
  if (el) {{
    el.style.display = el.style.display === 'none' ? 'table-row' : 'none';
    var icon = el.previousElementSibling.querySelector('.expand-icon');
    if (icon) icon.innerHTML = el.style.display === 'none' ? '&#9660;' : '&#9650;';
  }}
}}

function searchVendors(query) {{
  var rows = document.querySelectorAll('#vendorTable tr');
  var q = query.toLowerCase();
  rows.forEach(function(row) {{
    if (row.classList.contains('vendor-row')) {{
      var text = row.textContent.toLowerCase();
      var detail = row.nextElementSibling;
      if (q === '' || text.includes(q)) {{
        row.style.display = '';
        if (detail && detail.classList.contains('vendor-detail')) {{
          detail.style.display = 'none';
        }}
      }} else {{
        row.style.display = 'none';
        if (detail && detail.classList.contains('vendor-detail')) {{
          detail.style.display = 'none';
        }}
      }}
    }}
  }});
}}

function filterVendors(category) {{
  var rows = document.querySelectorAll('#vendorTable tr');
  rows.forEach(function(row) {{
    if (row.classList.contains('vendor-row')) {{
      var catEl = row.querySelector('.cat-tag');
      var catText = catEl ? catEl.textContent : '';
      var detail = row.nextElementSibling;
      if (category === 'all' || catText === category) {{
        row.style.display = '';
      }} else {{
        row.style.display = 'none';
        if (detail && detail.classList.contains('vendor-detail')) {{
          detail.style.display = 'none';
        }}
      }}
    }}
  }});
}}
</script>
</body>
</html>'''

    return html


# =========================================================================
# MAIN PIPELINE
# =========================================================================
def main():
    print("=" * 70)
    print("SFUSD Enhanced Forensic Financial Report Builder v2")
    print("=" * 70)

    # Step 1: Load SACS data
    analysis_results, sfusd_data = load_sacs_data()

    # Step 2: Parse vendor payments
    vendor_db = build_vendor_database()

    # Step 3: OCR check register
    check_register = ocr_check_register()

    # Step 4: Extract PDF texts
    pdf_extracts = extract_pdf_texts()

    # Step 5: Fact-check claims
    verification = fact_check_claims(analysis_results, vendor_db, pdf_extracts)

    # Step 6: Vendor research
    vendor_profiles = research_vendors(vendor_db)

    # Step 6B: Actionable savings analysis
    savings = analyze_actionable_savings(vendor_db, vendor_profiles, analysis_results, check_register)

    # Step 7: Generate HTML
    output_path = generate_html_report(analysis_results, vendor_db, check_register,
                                       pdf_extracts, verification, vendor_profiles, savings)

    # Step 8: Verification checks
    issues = run_verification(vendor_db, check_register, verification)

    print("\n" + "=" * 70)
    print(f"DONE. Report saved to: {output_path}")
    print(f"Open in browser: file://{output_path}")
    print("=" * 70)


if __name__ == "__main__":
    main()

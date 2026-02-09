#!/usr/bin/env python3
"""
SFUSD Forensic Financial Analysis — Maximizing Teacher Salary Plan
Parses SACS data, benchmarks against peer districts, generates analysis tables.
"""

import csv
import json
import os
import sys
from collections import defaultdict
from pathlib import Path

BASE_DIR = Path("/Users/jordancrawford/Desktop/Claude Code/Erin/sfusd-documents")
SACS_DIR = BASE_DIR / "sacs-data"
OUTPUT_DIR = BASE_DIR / "analysis" / "data"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# SFUSD identifiers
SFUSD_CCODE = "38"
SFUSD_DCODE = "68478"
SFUSD_CDS = "38684780000000"

# Peer district CDSCodes for benchmarking
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

# SACS Object Code categories (California School Accounting Manual)
OBJECT_CATEGORIES = {
    "1xxx": "Certificated Salaries",
    "2xxx": "Classified Salaries",
    "3xxx": "Employee Benefits",
    "4xxx": "Books and Supplies",
    "5xxx": "Services and Other Operating Expenditures",
    "6xxx": "Capital Outlay",
    "7xxx": "Other Outgo",
    "8xxx": "Revenue",
    "9xxx": "Fund Balance Components",
}

# SACS Function Code categories (from California School Accounting Manual)
FUNCTION_CATEGORIES = {
    "0000": "Not Applicable (Revenue/Balance Sheet)",
    "1000": "Instruction",
    "1110": "SpEd: Separate Classes",
    "1120": "SpEd: Resource Specialist",
    "1130": "SpEd: Supplemental in Regular",
    "1180": "SpEd: Nonpublic Agencies/Schools",
    "1190": "SpEd: Other Specialized",
    "2100": "Instructional Supervision & Administration",
    "2110": "Instructional Supervision",
    "2120": "Instructional Research",
    "2130": "Curriculum Development",
    "2140": "In-house Staff Development",
    "2150": "Instructional Admin of Special Projects",
    "2200": "Admin Unit of Multidistrict SELPA",
    "2420": "Instructional Library, Media & Technology",
    "2490": "Other Instructional Resources",
    "2495": "Parent Participation",
    "2700": "School Administration",
    "3110": "Guidance and Counseling",
    "3120": "Psychological Services",
    "3130": "Attendance and Social Work",
    "3140": "Health Services",
    "3150": "Speech Pathology and Audiology",
    "3160": "Pupil Testing Services",
    "3600": "Pupil Transportation",
    "3700": "Food Services",
    "3900": "Other Pupil Services",
    "4000": "Ancillary Services",
    "4100": "School-Sponsored Co-curricular",
    "4200": "School-Sponsored Athletics",
    "4900": "Other Ancillary Services",
    "5000": "Community Services",
    "5100": "Community Recreation",
    "5400": "Civic Services",
    "5900": "Other Community Services",
    "6000": "Enterprise",
    "7100": "Board and Superintendent",
    "7110": "Board",
    "7120": "Staff Relations and Negotiations",
    "7150": "Superintendent",
    "7180": "Public Information",
    "7190": "External Financial Audit - Single",
    "7191": "External Financial Audit - Other",
    "7200": "Other General Administration",
    "7210": "Indirect Cost Transfers",
    "7300": "Fiscal Services",
    "7310": "Budgeting",
    "7320": "Accounts Receivable",
    "7330": "Accounts Payable",
    "7340": "Payroll",
    "7350": "Financial Accounting",
    "7360": "Project-Specific Accounting",
    "7370": "Internal Auditing",
    "7380": "Property Accounting",
    "7390": "Other Fiscal Services",
    "7400": "Personnel/Human Resources",
    "7410": "Staff Development",
    "7430": "Credentials",
    "7490": "Other Personnel/HR Services",
    "7500": "Central Support",
    "7510": "Planning, Research, Development & Eval",
    "7530": "Purchasing",
    "7540": "Warehousing and Distribution",
    "7550": "Printing, Publishing, Duplicating",
    "7600": "All Other General Administration",
    "7700": "Centralized Data Processing",
    "8100": "Plant Maintenance and Operations",
    "8110": "Maintenance",
    "8200": "Operations",
    "8300": "Security",
    "8400": "Other Plant Maintenance & Operations",
    "8500": "Facilities Acquisition and Construction",
    "8700": "Facilities Rents and Leases",
    "9100": "Debt Service",
    "9200": "Transfers Between Agencies",
    "9300": "Interfund Transfers",
}

# Central admin function codes (BLA analysis categories)
# This matches the BLA's definition of "central administration"
ADMIN_FUNCTION_CODES = {
    "2100", "2110", "2120", "2130", "2140", "2150",  # Instructional Supervision & Admin
    "7100", "7110", "7120", "7150", "7180", "7190", "7191",  # Board & Superintendent
    "7200", "7210",  # Other General Administration
    "7300", "7310", "7320", "7330", "7340", "7350", "7360", "7370", "7380", "7390",  # Fiscal Services
    "7400", "7410", "7430", "7490",  # Personnel/HR
    "7500", "7510", "7530", "7540", "7550",  # Central Support
    "7600",  # All Other General Admin
    "7700",  # Centralized Data Processing
}

# Narrow admin = only top-level admin (Board, Superintendent, General Admin)
NARROW_ADMIN_CODES = {
    "7100", "7110", "7120", "7150", "7180", "7190", "7191",  # Board & Superintendent
    "7200", "7210",  # Other General Administration
    "7600",  # All Other General Admin
}

# Broader admin = includes school admin
BROAD_ADMIN_CODES = ADMIN_FUNCTION_CODES | {"2700"}

# Services/consulting object codes
SERVICES_OBJECT_RANGE = range(5000, 6000)  # 5xxx


def parse_sfusd_csv(filepath):
    """Parse SFUSD-format SACS CSV (ua-fy2020-21, ua-fy2021-22)."""
    records = []
    with open(filepath, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            fund = row['Fund'].strip().strip('"')
            function = row['Function'].strip().strip('"')
            obj = row['Object'].strip().strip('"')
            resource = row['Resource'].strip().strip('"')
            value = float(row['Value']) if row['Value'] else 0.0
            colcode = row['Colcode'].strip().strip('"')
            period = row['Period'].strip().strip('"')
            fy = row['Fiscalyear'].strip().strip('"')

            records.append({
                'fiscal_year': fy,
                'period': period,
                'col_code': colcode,
                'fund': fund,
                'resource': resource,
                'function': function,
                'object': obj,
                'value': value,
            })
    return records


def parse_statewide_csv(filepath, cds_codes=None, reporting_period=None):
    """Parse statewide extract UserGLs.csv, filtering by CDS codes."""
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


def get_object_category(obj_code):
    """Return high-level category for an object code."""
    if not obj_code:
        return "Unknown"
    first = obj_code[0] if len(obj_code) >= 1 else "0"
    return {
        '1': 'Certificated Salaries',
        '2': 'Classified Salaries',
        '3': 'Employee Benefits',
        '4': 'Books and Supplies',
        '5': 'Services & Operating',
        '6': 'Capital Outlay',
        '7': 'Other Outgo',
        '8': 'Revenue',
        '9': 'Fund Balance',
    }.get(first, 'Unknown')


def analyze_sfusd_by_function(records, fund_filter="01"):
    """Analyze SFUSD spending by function code for a given fund."""
    spending = defaultdict(float)
    for r in records:
        if r['fund'] != fund_filter:
            continue
        obj = r['object']
        if not obj or obj[0] not in ('1', '2', '3', '4', '5', '6', '7'):
            continue  # Skip revenue and fund balance entries
        func = r['function']
        spending[func] += r['value']
    return dict(spending)


def analyze_sfusd_by_object(records, fund_filter="01"):
    """Analyze SFUSD spending by object code category for a given fund."""
    spending = defaultdict(float)
    for r in records:
        if r['fund'] != fund_filter:
            continue
        obj = r['object']
        if not obj:
            continue
        cat = get_object_category(obj)
        spending[cat] += r['value']
    return dict(spending)


def analyze_admin_spending(records, fund_filter="01"):
    """Calculate admin spending vs total expenditures."""
    admin_total = 0.0
    total_expenditures = 0.0
    for r in records:
        if r['fund'] != fund_filter:
            continue
        obj = r['object']
        if not obj or obj[0] not in ('1', '2', '3', '4', '5', '6', '7'):
            continue
        val = r['value']
        total_expenditures += val
        func = r['function']
        if func in ADMIN_FUNCTION_CODES:
            admin_total += val
    return admin_total, total_expenditures


def analyze_services_spending(records, fund_filter="01"):
    """Extract all Object 5xxx (Services & Operating) spending by function."""
    services = defaultdict(float)
    total_services = 0.0
    for r in records:
        if r['fund'] != fund_filter:
            continue
        obj = r['object']
        if not obj or not obj.startswith('5'):
            continue
        val = r['value']
        total_services += val
        func = r['function']
        func_name = FUNCTION_CATEGORIES.get(func, f"Function {func}")
        services[func_name] += val
    return total_services, dict(services)


def get_fund_balance(records, fund_filter="01"):
    """Extract ending fund balance components from SACS data."""
    balance = {}
    for r in records:
        if r['fund'] != fund_filter:
            continue
        obj = r['object']
        if not obj or not obj.startswith('9'):
            continue
        balance[obj] = r['value']
    return balance


def calculate_revenue(records, fund_filter="01"):
    """Calculate total revenue from Object 8xxx codes."""
    total = 0.0
    categories = defaultdict(float)
    for r in records:
        if r['fund'] != fund_filter:
            continue
        obj = r['object']
        if not obj or not obj.startswith('8'):
            continue
        val = r['value']
        total += val
        # Group by sub-category
        if obj.startswith('80') or obj.startswith('81'):
            categories['LCFF Sources'] += val
        elif obj.startswith('82'):
            categories['Federal Revenue'] += val
        elif obj.startswith('83') or obj.startswith('84') or obj.startswith('85'):
            categories['Other State Revenue'] += val
        elif obj.startswith('86') or obj.startswith('87'):
            categories['Other Local Revenue'] += val
        elif obj.startswith('89'):
            categories['Interfund Transfers In'] += val
        else:
            categories['Other Revenue'] += val
    return total, dict(categories)


def format_currency(amount):
    """Format a number as currency."""
    if amount >= 1_000_000:
        return f"${amount/1_000_000:,.1f}M"
    elif amount >= 1_000:
        return f"${amount/1_000:,.0f}K"
    else:
        return f"${amount:,.0f}"


def format_pct(value):
    """Format as percentage."""
    return f"{value:.1f}%"


# ============================================================================
# MAIN ANALYSIS
# ============================================================================

def run_sfusd_analysis():
    """Run the complete SFUSD financial analysis."""
    print("=" * 80)
    print("SFUSD FORENSIC FINANCIAL ANALYSIS")
    print("=" * 80)

    results = {}

    # ------------------------------------------------------------------
    # Phase 1A: Parse SFUSD SACS data (FY2020-21 and FY2021-22)
    # ------------------------------------------------------------------
    print("\n--- Phase 1A: Parsing SFUSD SACS CSV Data ---")

    sfusd_data = {}
    for fy_dir, fy_label, filename in [
        ("ua-fy2020-21", "FY2020-21", "sfusd_usergl_fy2020-21.csv"),
        ("ua-fy2021-22", "FY2021-22", "sfusd_usergl_fy2021-22.csv"),
    ]:
        filepath = SACS_DIR / fy_dir / filename
        if filepath.exists():
            print(f"  Parsing {filepath.name} ...")
            records = parse_sfusd_csv(filepath)
            sfusd_data[fy_label] = records
            print(f"    {len(records)} line items loaded")

    # ------------------------------------------------------------------
    # Phase 1A: Admin spending analysis (SFUSD multi-year)
    # ------------------------------------------------------------------
    print("\n--- Admin Spending Analysis (SFUSD) ---")
    admin_results = {}
    for fy_label, records in sfusd_data.items():
        admin_total, total_exp = analyze_admin_spending(records)
        admin_pct = (admin_total / total_exp * 100) if total_exp else 0
        admin_results[fy_label] = {
            'admin_total': admin_total,
            'total_expenditures': total_exp,
            'admin_pct': admin_pct,
        }
        print(f"  {fy_label}:")
        print(f"    Admin (Func 2100,2200,3100-3500): {format_currency(admin_total)}")
        print(f"    Total Expenditures (Fund 01):      {format_currency(total_exp)}")
        print(f"    Admin as % of Total:               {format_pct(admin_pct)}")

    results['admin_spending'] = admin_results

    # ------------------------------------------------------------------
    # Function-level breakdown
    # ------------------------------------------------------------------
    print("\n--- Spending by Function Code (General Fund, Most Recent Year) ---")
    most_recent_fy = list(sfusd_data.keys())[-1]
    func_spending = analyze_sfusd_by_function(sfusd_data[most_recent_fy])
    sorted_funcs = sorted(func_spending.items(), key=lambda x: -abs(x[1]))
    func_table = []
    for func, val in sorted_funcs:
        func_name = FUNCTION_CATEGORIES.get(func, f"Unknown ({func})")
        func_table.append({
            'function_code': func,
            'function_name': func_name,
            'amount': val,
        })
        print(f"  {func} {func_name:50s} {format_currency(val):>12s}")
    results['function_breakdown'] = func_table

    # ------------------------------------------------------------------
    # Object-level breakdown
    # ------------------------------------------------------------------
    print("\n--- Spending by Object Category (General Fund) ---")
    for fy_label, records in sfusd_data.items():
        obj_spending = analyze_sfusd_by_object(records)
        print(f"  {fy_label}:")
        for cat in ['Certificated Salaries', 'Classified Salaries', 'Employee Benefits',
                     'Books and Supplies', 'Services & Operating', 'Capital Outlay', 'Other Outgo']:
            val = obj_spending.get(cat, 0)
            print(f"    {cat:40s} {format_currency(val):>12s}")

    # ------------------------------------------------------------------
    # Services spending (Object 5xxx) - consultant/contractor analysis
    # ------------------------------------------------------------------
    print("\n--- Services & Operating Expenditures (Object 5xxx) ---")
    services_results = {}
    for fy_label, records in sfusd_data.items():
        total_svc, svc_by_func = analyze_services_spending(records)
        services_results[fy_label] = {
            'total': total_svc,
            'by_function': svc_by_func,
        }
        print(f"  {fy_label} Total Services: {format_currency(total_svc)}")
        sorted_svc = sorted(svc_by_func.items(), key=lambda x: -abs(x[1]))
        for func_name, val in sorted_svc[:10]:
            print(f"    {func_name:50s} {format_currency(val):>12s}")
    results['services_spending'] = services_results

    # ------------------------------------------------------------------
    # Revenue analysis
    # ------------------------------------------------------------------
    print("\n--- Revenue Analysis (General Fund) ---")
    revenue_results = {}
    for fy_label, records in sfusd_data.items():
        total_rev, rev_cats = calculate_revenue(records)
        revenue_results[fy_label] = {
            'total': total_rev,
            'categories': rev_cats,
        }
        print(f"  {fy_label} Total Revenue: {format_currency(total_rev)}")
        for cat, val in sorted(rev_cats.items(), key=lambda x: -x[1]):
            print(f"    {cat:40s} {format_currency(val):>12s}")
    results['revenue'] = revenue_results

    # ------------------------------------------------------------------
    # Fund Balance analysis
    # ------------------------------------------------------------------
    print("\n--- Fund Balance (General Fund, Object 9xxx) ---")
    balance_results = {}
    for fy_label, records in sfusd_data.items():
        balances = get_fund_balance(records)
        balance_results[fy_label] = balances
        # Key balance codes:
        # 9791 = Designated for Economic Uncertainties (reserve)
        # 9790 = Other Designations
        # 9789 = Ending Fund Balance
        print(f"  {fy_label}:")
        for code, val in sorted(balances.items()):
            print(f"    Object {code}: {format_currency(val):>15s}")
    results['fund_balance'] = balance_results

    # ------------------------------------------------------------------
    # Phase 1B: Peer District Benchmarking (Statewide Extract)
    # ------------------------------------------------------------------
    statewide_file = SACS_DIR / "statewide-extract-fy2024-25" / "UserGLs.csv"
    if statewide_file.exists():
        print("\n--- Phase 1B: Peer District Benchmarking ---")
        print(f"  Loading statewide extract (this may take a minute)...")

        peer_cds = set(PEER_DISTRICTS.keys())
        # Parse only BS1 (budget) period for the most recent filing
        peer_records = parse_statewide_csv(statewide_file, cds_codes=peer_cds, reporting_period="BS1")
        print(f"  Loaded {len(peer_records)} peer district records")

        # Group by district
        by_district = defaultdict(list)
        for r in peer_records:
            by_district[r['cds_code']].append(r)

        # Admin spending comparison
        print("\n  --- Admin Spending Comparison (FY2024-25 Budget) ---")
        peer_admin = {}
        for cds, name in PEER_DISTRICTS.items():
            district_records = by_district.get(cds, [])
            if not district_records:
                print(f"    {name}: No data found")
                continue
            admin_total = 0.0
            total_exp = 0.0
            for r in district_records:
                if r['fund'] != '01':
                    continue
                obj = r['object']
                if not obj or obj[0] not in ('1', '2', '3', '4', '5', '6', '7'):
                    continue
                val = r['value']
                total_exp += val
                func = r['function']
                if func in ADMIN_FUNCTION_CODES:
                    admin_total += val

            admin_pct = (admin_total / total_exp * 100) if total_exp else 0
            peer_admin[name] = {
                'admin_total': admin_total,
                'total_expenditures': total_exp,
                'admin_pct': admin_pct,
            }
            print(f"    {name:30s} Admin: {format_currency(admin_total):>12s}  "
                  f"Total: {format_currency(total_exp):>12s}  "
                  f"Admin%: {format_pct(admin_pct):>6s}")

        results['peer_admin_comparison'] = peer_admin

        # Services spending comparison
        print("\n  --- Services Spending Comparison (Object 5xxx) ---")
        peer_services = {}
        for cds, name in PEER_DISTRICTS.items():
            district_records = by_district.get(cds, [])
            if not district_records:
                continue
            total_svc = 0.0
            total_exp = 0.0
            for r in district_records:
                if r['fund'] != '01':
                    continue
                obj = r['object']
                if not obj or obj[0] not in ('1', '2', '3', '4', '5', '6', '7'):
                    continue
                val = r['value']
                total_exp += val
                if obj.startswith('5'):
                    total_svc += val

            svc_pct = (total_svc / total_exp * 100) if total_exp else 0
            peer_services[name] = {
                'services_total': total_svc,
                'total_expenditures': total_exp,
                'services_pct': svc_pct,
            }
            print(f"    {name:30s} Services: {format_currency(total_svc):>12s}  "
                  f"Total: {format_currency(total_exp):>12s}  "
                  f"Svc%: {format_pct(svc_pct):>6s}")

        results['peer_services_comparison'] = peer_services

        # Salary spending comparison
        print("\n  --- Salary Spending Comparison (Objects 1xxx + 2xxx) ---")
        peer_salary = {}
        for cds, name in PEER_DISTRICTS.items():
            district_records = by_district.get(cds, [])
            if not district_records:
                continue
            cert_sal = 0.0
            class_sal = 0.0
            total_exp = 0.0
            for r in district_records:
                if r['fund'] != '01':
                    continue
                obj = r['object']
                if not obj or obj[0] not in ('1', '2', '3', '4', '5', '6', '7'):
                    continue
                val = r['value']
                total_exp += val
                if obj.startswith('1'):
                    cert_sal += val
                elif obj.startswith('2'):
                    class_sal += val

            sal_total = cert_sal + class_sal
            sal_pct = (sal_total / total_exp * 100) if total_exp else 0
            peer_salary[name] = {
                'certificated': cert_sal,
                'classified': class_sal,
                'total_salary': sal_total,
                'total_expenditures': total_exp,
                'salary_pct': sal_pct,
            }
            print(f"    {name:30s} Cert: {format_currency(cert_sal):>12s}  "
                  f"Class: {format_currency(class_sal):>12s}  "
                  f"Total: {format_currency(total_exp):>12s}  "
                  f"Sal%: {format_pct(sal_pct):>6s}")

        results['peer_salary_comparison'] = peer_salary

        # Detailed function breakdown for SFUSD from statewide data
        print("\n  --- SFUSD Function Breakdown (FY2024-25 Budget, Statewide Extract) ---")
        sfusd_sw = by_district.get(SFUSD_CDS, [])
        if sfusd_sw:
            func_totals = defaultdict(float)
            for r in sfusd_sw:
                if r['fund'] != '01':
                    continue
                obj = r['object']
                if not obj or obj[0] not in ('1', '2', '3', '4', '5', '6', '7'):
                    continue
                func_totals[r['function']] += r['value']

            sorted_funcs_sw = sorted(func_totals.items(), key=lambda x: -abs(x[1]))
            for func, val in sorted_funcs_sw:
                func_name = FUNCTION_CATEGORIES.get(func, f"Unknown ({func})")
                is_admin = " [ADMIN]" if func in ADMIN_FUNCTION_CODES else ""
                print(f"    {func} {func_name:50s} {format_currency(val):>12s}{is_admin}")
            results['sfusd_statewide_function_breakdown'] = {
                func: val for func, val in sorted_funcs_sw
            }

    # ------------------------------------------------------------------
    # Save results as JSON for report generation
    # ------------------------------------------------------------------
    output_file = OUTPUT_DIR / "analysis_results.json"

    # Convert results to JSON-serializable format
    def make_serializable(obj):
        if isinstance(obj, dict):
            return {str(k): make_serializable(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [make_serializable(i) for i in obj]
        elif isinstance(obj, float):
            return round(obj, 2)
        return obj

    with open(output_file, 'w') as f:
        json.dump(make_serializable(results), f, indent=2)
    print(f"\n  Results saved to {output_file}")

    return results


if __name__ == "__main__":
    results = run_sfusd_analysis()
    print("\n" + "=" * 80)
    print("ANALYSIS COMPLETE")
    print("=" * 80)

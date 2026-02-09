#!/usr/bin/env python3
"""
SFUSD Documents — Round 2 Download Script
==========================================
Fills gaps identified in the first round:
- Re-downloads 6 zero-byte files from round 1
- Adds salary schedules (all bargaining units)
- Adds missing comparable contracts (OEA, SJTA, UTLA 2022-25)
- Adds UASF administrator CBA 2025-2028
- Adds Civil Grand Jury "Not Making the Grade" report
- Adds Fiscal Stabilization Plan Dec 2025 + board presentations
- Adds FY 2024-25 Budget Book (1st Reading)
- Adds UESF bargaining updates page
- Adds PEEF & parcel tax oversight info
- Adds CDE SACS data viewer / DataQuest pages
- Adds historical 1979 strike coverage
- Adds recent board presentations (portfolio planning, staffing model)
"""

import os
import sys
import time
import logging
import hashlib
from datetime import datetime

import requests
from bs4 import BeautifulSoup

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(BASE_DIR, "download_round2_errors.log")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, mode="w"),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

# ── Downloads manifest ────────────────────────────────────────────────
# Each entry: (url, folder, filename, description, type)
#   type = "pdf" | "text" | "text_replace" (overwrite 0-byte files)

DOWNLOADS = [
    # ── FIX: Re-download 0-byte files from round 1 ──────────────────
    (
        "https://www.census.gov/quickfacts/sanfranciscocitycalifornia",
        "comparable-data",
        "census_quickfacts-sf_current.txt",
        "US Census QuickFacts for San Francisco — demographics, income, housing",
        "text_replace",
    ),
    (
        "https://www.ed-data.org/district/San-Francisco/San-Francisco-Unified",
        "comparable-data",
        "ed-data_sfusd-financial-profile_current.txt",
        "Ed-Data SFUSD financial profile — revenue/expenditure per pupil",
        "text_replace",
    ),
    (
        "https://nces.ed.gov/ccd/districtsearch/district_detail.asp?ID2=0634410",
        "comparable-data",
        "nces_sfusd-district-detail_current.txt",
        "NCES Common Core of Data — SFUSD district detail",
        "text_replace",
    ),
    (
        "https://transparentcalifornia.com/salaries/school-districts/san-francisco/san-francisco-unified/",
        "comparable-data",
        "transparent-ca_sfusd-salaries_current.txt",
        "Transparent California — SFUSD employee salary data",
        "text_replace",
    ),
    (
        "https://edsource.org/updates/school-districts-with-stalled-teacher-contract-negotiations-grows",
        "news-coverage",
        "edsource_stalled-negotiations-tracker_2025.txt",
        "EdSource tracker of stalled teacher contract negotiations statewide",
        "text_replace",
    ),
    (
        "https://edsource.org/updates/los-angeles-san-francisco-teachers-unions-vote-to-authorize-a-strike",
        "news-coverage",
        "edsource_strike-authorization_2025-12.txt",
        "EdSource — LA and SF teacher unions vote to authorize strikes",
        "text_replace",
    ),

    # ── Salary Schedules ─────────────────────────────────────────────
    (
        "https://uesf.org/wp-content/uploads/2018/06/2017-2020-Certificated-Salary-Schedule-with-Living-Wages-for-Teachers-add-on.pdf",
        "salary-schedules",
        "uesf_certificated-salary-schedule_2017-2020.pdf",
        "UESF certificated salary schedule 2017-2020 with living wage add-on",
        "pdf",
    ),
    (
        "https://www.sfusd.edu/information-employees/labor-relations/salary-schedules",
        "salary-schedules",
        "sfusd_salary-schedules-page_current.txt",
        "SFUSD salary schedules hub page — links to all bargaining unit schedules",
        "text",
    ),
    (
        "https://uesf.org/members/contracts-salary-schedules/",
        "salary-schedules",
        "uesf_contracts-salary-schedules-page_current.txt",
        "UESF contracts and salary schedules page — links to current and historical schedules",
        "text",
    ),

    # ── UASF Administrator CBA 2025-2028 ────────────────────────────
    (
        "https://go.boarddocs.com/ca/sfusd/Board.nsf/files/DNQUN57CD115/$file/Attachment%20F%20UASF%20CONTRACT%20July%201,%202025%20-%20June%2030,%202028.pdf",
        "labor-agreements",
        "uasf_cba_2025-2028.pdf",
        "UASF administrator collective bargaining agreement 2025-2028",
        "pdf",
    ),

    # ── Civil Grand Jury ─────────────────────────────────────────────
    (
        "https://media.api.sf.gov/documents/2023_CGJ_Report_Not_Making_the_Grade_-_San_Franciscos_Shortage_of_Credentialed_e7kssaM.pdf",
        "spending-analysis",
        "sf-grand-jury_not-making-the-grade-teacher-staffing_2023.pdf",
        "SF Civil Grand Jury 2022-23 — 'Not Making the Grade' teacher staffing report",
        "pdf",
    ),

    # ── Comparable Contracts ─────────────────────────────────────────
    (
        "https://utla.net/app/uploads/2023/04/UTLA-LAUSD-TA-2022-2025-CBA-Signed-4-24-23.docx-1.pdf",
        "comparable-contracts",
        "utla_cba-2022-2025_lausd.pdf",
        "UTLA-LAUSD collective bargaining agreement 2022-2025 (signed)",
        "pdf",
    ),
    (
        "https://edsource.org/wp-content/uploads/old/sjta_ta_copy.pdf",
        "comparable-contracts",
        "sjta_tentative-agreement_san-jose.pdf",
        "San Jose Teachers Association tentative agreement (EdSource copy)",
        "pdf",
    ),

    # ── Additional BoardDocs PDFs ────────────────────────────────────
    # Fiscal Stabilization Plan Dec 2025
    (
        "https://go.boarddocs.com/ca/sfusd/Board.nsf/files/DPF2360027C8/$file/12.16.25%20BOE%20Regular%20Meeting%20FSP%20Overview.pdf",
        "fiscal-oversight",
        "sfusd_fiscal-stabilization-plan_2025-12.pdf",
        "SFUSD Fiscal Stabilization Plan overview — December 16, 2025 BOE meeting",
        "pdf",
    ),
    # Portfolio Planning Presentation (Aug 2024)
    (
        "https://go.boarddocs.com/ca/sfusd/Board.nsf/files/D8K4WK0D8DE7/$file/%5BFINAL%5D%208_27_24%20-%20BOE%20Workshop%20Portfolio%20Planning%20Presentation.pdf",
        "board-presentations",
        "sfusd_portfolio-planning-presentation_2024-08-27.pdf",
        "BOE workshop portfolio planning presentation — school consolidation analysis",
        "pdf",
    ),
    # Staffing Model Update (Jan 2025)
    (
        "https://go.boarddocs.com/ca/sfusd/Board.nsf/files/DD8VZV833957/$file/1.28.25%20-%20Staffing%20Model%20Update%20-%20Board%20of%20Education.pdf",
        "board-presentations",
        "sfusd_staffing-model-update_2025-01-28.pdf",
        "SFUSD staffing model update presentation — January 28, 2025",
        "pdf",
    ),
    # FY 2024-25 Budget Book (1st Reading)
    (
        "https://go.boarddocs.com/ca/sfusd/Board.nsf/files/D623GW06DD48/$file/2024-25%20Recommended%20Budget%20book%20(1st%20Reading)_draft%206-7-24.pdf",
        "budgets/fy2024-25",
        "sfusd_recommended-budget-book-full_fy2024-25.pdf",
        "FY 2024-25 recommended budget book full version (1st Reading draft 6/7/24)",
        "pdf",
    ),

    # ── UESF Bargaining Updates ──────────────────────────────────────
    (
        "https://uesf.org/news/bargaining-updates/",
        "negotiations",
        "uesf_bargaining-updates-page_2025-2026.txt",
        "UESF bargaining updates page — all 2025-2026 negotiation updates and proposals",
        "text",
    ),
    (
        "https://uesf.org/members/contracts-salary-schedules/",
        "negotiations",
        "uesf_contracts-page_current.txt",
        "UESF contracts page — links to all current and historical CBAs",
        "text",
    ),

    # ── PEEF & Parcel Tax ────────────────────────────────────────────
    (
        "https://www.sfusd.edu/information-community/public-education-enrichment-fund-peef",
        "parcel-tax",
        "sfusd_peef-overview-page_current.txt",
        "SFUSD Public Education Enrichment Fund (PEEF) overview — $94M/year program",
        "text",
    ),
    (
        "https://www.sfusd.edu/advisory-councils-committees/parcel-tax-oversight-committee",
        "parcel-tax",
        "sfusd_parcel-tax-oversight-committee_current.txt",
        "SFUSD Parcel Tax Oversight Committee page — QTEA and FWEA compliance",
        "text",
    ),

    # ── CDE Data Portals ─────────────────────────────────────────────
    (
        "https://www.cde.ca.gov/ds/fd/dv/",
        "comparable-data",
        "cde_sacs-data-viewer-page_current.txt",
        "CDE SACS Data Viewer landing page — structured budget/actuals data portal",
        "text",
    ),
    (
        "https://www.cde.ca.gov/ds/fd/ec/currentexpense.asp",
        "comparable-data",
        "cde_current-expense-of-education_current.txt",
        "CDE Current Expense of Education page — per-pupil spending data",
        "text",
    ),

    # ── SFUSD Budget Archives Page ───────────────────────────────────
    (
        "https://www.sfusd.edu/about-sfusd/budget-and-lcap/budget-and-lcaps-previous-fiscal-years",
        "budgets",
        "sfusd_budget-archives-page_all-years.txt",
        "SFUSD budget and LCAP archives — links to all prior fiscal year documents",
        "text",
    ),
    (
        "https://www.sfusd.edu/about-sfusd/budget-and-lcap/budget-and-lcap-archives",
        "budgets",
        "sfusd_budget-lcap-archives-page_current.txt",
        "SFUSD budget and LCAP archives (alternate URL) — document links",
        "text",
    ),

    # ── SFUSD Labor Relations ────────────────────────────────────────
    (
        "https://www.sfusd.edu/information-employees/labor-relations/labor-contracts-mous-and-salary-schedules",
        "labor-agreements",
        "sfusd_labor-contracts-mous-page_current.txt",
        "SFUSD labor contracts, MOUs, and salary schedules hub page",
        "text",
    ),
    (
        "https://www.sfusd.edu/information-employees/labor-relations",
        "labor-agreements",
        "sfusd_labor-relations-page_current.txt",
        "SFUSD Labor Relations department page — all bargaining units",
        "text",
    ),

    # ── Bond Program ─────────────────────────────────────────────────
    (
        "https://www.sfusd.edu/bond/financialreports",
        "bond-program",
        "sfusd_bond-financial-reports-page_current.txt",
        "SFUSD bond program financial reporting page — quarterly/annual report links",
        "text",
    ),

    # ── Enrollment Data / DataQuest ──────────────────────────────────
    (
        "https://www.cde.ca.gov/ds/ad/filesenr.asp",
        "enrollment-data",
        "cde_enrollment-data-files-page_current.txt",
        "CDE enrollment data files download page — historical enrollment by district",
        "text",
    ),

    # ── Historical 1979 Strike ───────────────────────────────────────
    (
        "https://www.foundsf.org/index.php?title=Teacher_Strikes",
        "news-coverage",
        "foundsf_teacher-strikes-history_1979.txt",
        "FoundSF community history — San Francisco teacher strikes including 1979",
        "text",
    ),

    # ── Additional News / Analysis ───────────────────────────────────
    (
        "https://www.sfeducationalliance.com/blog/sfusd-budget-exploration",
        "news-coverage",
        "sf-education-alliance_budget-exploration_2023.txt",
        "SF Education Alliance — SFUSD 2022-23 and 2023-24 budget numbers and narratives analysis",
        "text",
    ),

    # ── PERB Filing Info ─────────────────────────────────────────────
    (
        "https://perb.ca.gov/how-to-file-an-unfair-practice-charge/",
        "legal",
        "perb_unfair-practice-charge-info_current.txt",
        "PERB — how to file an unfair practice charge (reference for legal context)",
        "text",
    ),

    # ── AB 602 Special Education Funding ─────────────────────────────
    (
        "https://www.cde.ca.gov/fg/fo/r14/ab60224result.asp",
        "fiscal-oversight",
        "cde_ab602-sped-funding-results_fy2024.txt",
        "CDE AB 602 special education funding results — SELPA allocations",
        "text",
    ),

    # ── Board Meeting Minutes with Contract Approvals ────────────────
    (
        "https://go.boarddocs.com/ca/sfusd/Board.nsf/files/D5PTHV7781B9/$file/MINUTES%20Regular%20Meeting%20of%20April%2016,%202024%20Hybrid.pdf",
        "board-presentations",
        "sfusd_board-minutes-contract-approvals_2024-04-16.pdf",
        "Board meeting minutes April 16 2024 — includes vendor contract consent items",
        "pdf",
    ),
    (
        "https://go.boarddocs.com/ca/sfusd/Board.nsf/files/DENRXC701A4C/$file/DRAFT%20MINUTES%20Regular%20Meeting%20of%20February%2011,%202025%20Hybrid%20(1).pdf",
        "board-presentations",
        "sfusd_board-minutes-contract-approvals_2025-02-11.pdf",
        "Board meeting minutes Feb 11 2025 — includes vendor contract consent items",
        "pdf",
    ),
]


def download_pdf(url, filepath):
    """Download a PDF file."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=60, verify=True, allow_redirects=True)
        resp.raise_for_status()

        ct = resp.headers.get("Content-Type", "")
        if "html" in ct.lower() and len(resp.content) < 5000:
            log.warning(f"  Got HTML instead of PDF for {os.path.basename(filepath)}")
            return False

        with open(filepath, "wb") as f:
            f.write(resp.content)

        size = os.path.getsize(filepath)
        if size < 1000:
            log.warning(f"  PDF suspiciously small ({size} bytes): {os.path.basename(filepath)}")
            return False

        # Check PDF magic bytes
        with open(filepath, "rb") as f:
            header = f.read(5)
        if header[:4] != b"%PDF":
            log.warning(f"  Not a valid PDF (header: {header!r}): {os.path.basename(filepath)}")
            os.remove(filepath)
            return False

        log.info(f"  OK: {os.path.basename(filepath)} ({size:,} bytes)")
        return True

    except requests.exceptions.SSLError:
        log.warning(f"  SSL error, retrying without verification: {url}")
        try:
            resp = requests.get(url, headers=HEADERS, timeout=60, verify=False, allow_redirects=True)
            resp.raise_for_status()
            with open(filepath, "wb") as f:
                f.write(resp.content)
            size = os.path.getsize(filepath)
            log.info(f"  OK (SSL bypass): {os.path.basename(filepath)} ({size:,} bytes)")
            return True
        except Exception as e2:
            log.error(f"  FAILED (SSL bypass): {e2}")
            return False

    except Exception as e:
        log.error(f"  FAILED: {e}")
        return False


def save_web_page_as_text(url, filepath):
    """Download a web page and save as cleaned text."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=60, allow_redirects=True)
        resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "html.parser")

        # Remove script, style, nav, footer
        for tag in soup(["script", "style", "nav", "footer", "header", "noscript", "iframe"]):
            tag.decompose()

        text = soup.get_text(separator="\n", strip=True)

        # Collapse multiple blank lines
        lines = text.split("\n")
        cleaned = []
        prev_blank = False
        for line in lines:
            line = line.strip()
            if not line:
                if not prev_blank:
                    cleaned.append("")
                prev_blank = True
            else:
                cleaned.append(line)
                prev_blank = False

        content = "\n".join(cleaned).strip()

        # Write with source header
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(f"Source: {url}\n")
            f.write(f"Saved: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
            f.write("=" * 80 + "\n\n")
            f.write(content)

        size = os.path.getsize(filepath)
        if size < 200:
            log.warning(f"  Very small text file ({size} bytes): {os.path.basename(filepath)}")
            return False

        log.info(f"  OK: {os.path.basename(filepath)} ({size:,} bytes)")
        return True

    except requests.exceptions.SSLError:
        log.warning(f"  SSL error, retrying without verification: {url}")
        try:
            resp = requests.get(url, headers=HEADERS, timeout=60, verify=False, allow_redirects=True)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")
            for tag in soup(["script", "style", "nav", "footer", "header", "noscript", "iframe"]):
                tag.decompose()
            text = soup.get_text(separator="\n", strip=True)
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(f"Source: {url}\n")
                f.write(f"Saved: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
                f.write("=" * 80 + "\n\n")
                f.write(text)
            size = os.path.getsize(filepath)
            log.info(f"  OK (SSL bypass): {os.path.basename(filepath)} ({size:,} bytes)")
            return True
        except Exception as e2:
            log.error(f"  FAILED (SSL bypass): {e2}")
            return False

    except Exception as e:
        log.error(f"  FAILED: {e}")
        return False


def run_all_downloads():
    """Execute all downloads."""
    total = len(DOWNLOADS)
    success = 0
    failed = 0
    skipped = 0

    for i, (url, folder, filename, desc, dtype) in enumerate(DOWNLOADS, 1):
        filepath = os.path.join(BASE_DIR, folder, filename)

        # Create directory if needed
        os.makedirs(os.path.dirname(filepath), exist_ok=True)

        # Skip if already exists and not a replacement
        if dtype != "text_replace" and os.path.exists(filepath) and os.path.getsize(filepath) > 100:
            log.info(f"[{i}/{total}] SKIP (exists): {filename}")
            skipped += 1
            continue

        log.info(f"[{i}/{total}] Downloading: {filename}")
        log.info(f"  URL: {url}")

        if dtype == "pdf":
            ok = download_pdf(url, filepath)
        else:  # "text" or "text_replace"
            ok = save_web_page_as_text(url, filepath)

        if ok:
            success += 1
        else:
            failed += 1

        # Rate limit
        time.sleep(1.0)

    return success, failed, skipped


def update_manifest():
    """Regenerate manifest.md with all files across all categories."""
    manifest_path = os.path.join(BASE_DIR, "manifest.md")

    all_files = []
    for root, dirs, files in os.walk(BASE_DIR):
        # Skip hidden dirs and special files
        dirs[:] = [d for d in dirs if not d.startswith(".") and d != "_sources" and d != "__pycache__"]
        for f in sorted(files):
            if f.startswith(".") or f.endswith(".py") or f.endswith(".log"):
                continue
            if f in ("manifest.md", "manual_downloads.md", "cpra_request_template.md"):
                continue
            fp = os.path.join(root, f)
            rel = os.path.relpath(fp, BASE_DIR)
            size = os.path.getsize(fp)
            all_files.append((rel, size))

    all_files.sort()

    # Group by directory
    from collections import defaultdict
    by_dir = defaultdict(list)
    for rel, size in all_files:
        d = os.path.dirname(rel)
        by_dir[d].append((os.path.basename(rel), size))

    total_size = sum(s for _, s in all_files)

    with open(manifest_path, "w") as f:
        f.write("# SFUSD Documents Manifest\n\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n")
        f.write("## Summary\n\n")
        f.write(f"- **Total document files:** {len(all_files)}\n")
        f.write(f"- **Total size:** {total_size / 1_048_576:.1f} MB\n")

        dirs_with_files = [d for d in sorted(by_dir.keys()) if by_dir[d]]
        f.write(f"- **Categories:** {len(dirs_with_files)}\n\n")

        for d in sorted(by_dir.keys()):
            files_list = by_dir[d]
            f.write(f"## {d}/\n\n")
            if not files_list:
                f.write("*No files yet*\n\n")
                continue
            f.write("| File | Size |\n")
            f.write("|------|------|\n")
            for fname, size in sorted(files_list):
                if size >= 1_048_576:
                    size_str = f"{size / 1_048_576:.1f} MB"
                elif size >= 1024:
                    size_str = f"{size // 1024} KB"
                else:
                    size_str = f"{size} bytes"
                f.write(f"| `{fname}` | {size_str} |\n")
            f.write("\n")

    log.info(f"Manifest updated: {len(all_files)} files, {total_size / 1_048_576:.1f} MB")


def main():
    log.info("=" * 60)
    log.info("SFUSD Documents — Round 2 Download")
    log.info(f"Target: {BASE_DIR}")
    log.info(f"Downloads: {len(DOWNLOADS)} entries")
    log.info("=" * 60)

    success, failed, skipped = run_all_downloads()

    log.info("")
    log.info("=" * 60)
    log.info(f"RESULTS: {success} downloaded, {failed} failed, {skipped} skipped")
    log.info("=" * 60)

    update_manifest()

    if failed > 0:
        log.info(f"\nCheck {LOG_FILE} for error details.")

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""
Parse SFUSD Board Report of Checks PDFs using Tesseract OCR + geometric table reconstruction.

These PDFs are digitally rendered (Print-to-PDF from ReqPay12a ERP), not physical scans.
Tesseract at 300 DPI reads them more accurately than GPT-4o vision, for free.

Pipeline per month:
  1. pdftoppm -png -r 300 to convert PDF pages to images
  2. pytesseract.image_to_data() for word-level bounding boxes
  3. Geometric column assignment based on x-coordinates
  4. Row grouping by y-coordinate proximity
  5. Parse rows into check entries with multi-line support

Output: data/check_register_v2.json + data/check_register_v2_quality.json
"""

import json
import re
import subprocess
import sys
import tempfile
from collections import defaultdict
from pathlib import Path

import pytesseract
from PIL import Image

# ---------------------------------------------------------------------------
# CONFIGURATION
# ---------------------------------------------------------------------------
BASE_DIR = Path("/Users/jordancrawford/Desktop/Claude Code/Erin/sfusd-documents")
WARRANTS_DIR = BASE_DIR / "spending-analysis" / "warrants"
DATA_DIR = BASE_DIR / "analysis" / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

MONTHS = ["July", "August", "September", "October", "November", "December"]

# Cover letter net totals (from fund recap summary on last page of each PDF)
COVER_LETTER_TOTALS = {
    "July": 60523520.99,
    "August": 24700613.85,
    "September": 65280245.59,
    "October": 52194350.99,
    "November": 50948400.89,
    "December": 59059990.47,
}

# Cover letter check counts
COVER_LETTER_COUNTS = {
    "July": {"gross": 1088, "cancels": 22, "reissues": 2, "net": 1066},
    "August": {"gross": 457, "cancels": 27, "reissues": 0, "net": 430},
    "September": {"gross": 1242, "cancels": 14, "reissues": 0, "net": 1228},
    "October": {"gross": 1122, "cancels": 11, "reissues": 0, "net": 1111},
    "November": {"gross": 1123, "cancels": 31, "reissues": 0, "net": 1092},
    "December": {"gross": 1296, "cancels": 20, "reissues": 0, "net": 1276},
}

DPI = 300

# Column x-coordinate boundaries at 300 DPI (2550px wide page)
# Determined empirically from header row positions on page 2
COL_CHECK_NUM = (100, 400)      # Check Number: x ~ 195
COL_DATE = (400, 600)           # Check Date: x ~ 446
COL_VENDOR = (600, 1600)        # Vendor name: x ~ 647-1100+
COL_FD_OBJT = (1600, 1810)      # Fd-Objt: x ~ 1665
COL_EXP_AMT = (1810, 2100)      # Expensed Amount: x ~ 1866-1948
COL_CHECK_AMT = (2100, 2400)    # Check Amount: x ~ 2138-2323

# Patterns
RE_CHECK_NUM = re.compile(r'^(020\d{7}|120\d{7}|DDP-\d{8})$')
RE_DATE = re.compile(r'\d{2}/\d{2}/\d{4}')
RE_FD_OBJT = re.compile(r'^\d{2}-\d{4}$')
RE_AMOUNT = re.compile(r'^[\d,]+\.\d{2}$')
RE_ZEBRA_NOISE = re.compile(r'^[=:+~}{|3\d]*$')  # Zebra stripe artifacts


def pdf_to_images(pdf_path, tmpdir):
    """Convert PDF to PNG images at DPI. Returns sorted list of image paths."""
    subprocess.run(
        ["pdftoppm", "-png", "-r", str(DPI), str(pdf_path), f"{tmpdir}/page"],
        check=True, capture_output=True,
    )
    return sorted(Path(tmpdir).glob("page-*.png"))


def get_word_boxes(img_path):
    """Run Tesseract on an image, return list of word dicts with bounding boxes."""
    img = Image.open(str(img_path))
    df = pytesseract.image_to_data(img, output_type=pytesseract.Output.DATAFRAME)
    # Filter to actual recognized text with positive confidence
    df = df[df['conf'] > 0].copy()
    words = []
    for _, row in df.iterrows():
        text = str(row['text']).strip()
        if not text:
            continue
        words.append({
            'x': int(row['left']),
            'y': int(row['top']),
            'w': int(row['width']),
            'h': int(row['height']),
            'conf': float(row['conf']),
            'text': text,
        })
    return words


def assign_column(x):
    """Assign a word to a column based on its x-coordinate."""
    if COL_CHECK_NUM[0] <= x < COL_CHECK_NUM[1]:
        return 'check_num'
    elif COL_DATE[0] <= x < COL_DATE[1]:
        return 'date'
    elif COL_VENDOR[0] <= x < COL_VENDOR[1]:
        return 'vendor'
    elif COL_FD_OBJT[0] <= x < COL_FD_OBJT[1]:
        return 'fd_objt'
    elif COL_EXP_AMT[0] <= x < COL_EXP_AMT[1]:
        return 'exp_amt'
    elif COL_CHECK_AMT[0] <= x < COL_CHECK_AMT[1]:
        return 'check_amt'
    return None


def group_into_rows(words, y_tolerance=20):
    """Group words into rows by y-coordinate proximity."""
    if not words:
        return []
    sorted_words = sorted(words, key=lambda w: (w['y'], w['x']))
    rows = []
    current_row = [sorted_words[0]]
    current_y = sorted_words[0]['y']

    for word in sorted_words[1:]:
        if abs(word['y'] - current_y) <= y_tolerance:
            current_row.append(word)
        else:
            rows.append(sorted(current_row, key=lambda w: w['x']))
            current_row = [word]
            current_y = word['y']
    if current_row:
        rows.append(sorted(current_row, key=lambda w: w['x']))
    return rows


def clean_text(text):
    """Remove zebra stripe artifacts from text."""
    # Strip leading noise characters from dates: "=07/15/2025" -> "07/15/2025"
    text = re.sub(r'^[=:+~}{|]+', '', text)
    # Strip leading single digits that are zebra noise: "3=07/15/2025" -> "07/15/2025"
    text = re.sub(r'^\d[=:+~}{|]+', '', text)
    # Remove curly braces, tildes from check numbers: "0200000005}" -> "0200000005"
    text = re.sub(r'[{}~]', '', text)
    return text.strip()


def parse_amount(text):
    """Parse a dollar amount string. Returns float or None."""
    text = text.replace(',', '').replace('$', '').strip()
    # Remove any trailing asterisk
    text = text.rstrip('*').strip()
    try:
        return float(text)
    except ValueError:
        return None


def extract_row_fields(row_words):
    """Extract structured fields from a row of words. Returns dict."""
    fields = {
        'check_num': [],
        'date': [],
        'vendor': [],
        'fd_objt': [],
        'exp_amt': [],
        'check_amt': [],
        'other': [],
    }

    for word in row_words:
        col = assign_column(word['x'])
        if col:
            fields[col].append(word)
        else:
            fields['other'].append(word)

    result = {}

    # Check number
    cn_texts = [clean_text(w['text']) for w in fields['check_num']]
    cn_joined = ' '.join(cn_texts).strip()
    if cn_joined:
        # Try to extract a valid check number
        # Handle "DDP-00000046" which may come as one token or "DDP" + "-" + "00000046"
        cn_clean = cn_joined.replace(' ', '')
        if RE_CHECK_NUM.match(cn_clean):
            result['check_num'] = cn_clean
        elif cn_clean.startswith('DDP') and '-' in cn_clean:
            # Try padding: DDP-1234 -> DDP-00001234
            parts = cn_clean.split('-', 1)
            padded = f"DDP-{parts[1].zfill(8)}"
            if RE_CHECK_NUM.match(padded):
                result['check_num'] = padded

    # Date
    date_texts = [clean_text(w['text']) for w in fields['date']]
    for dt in date_texts:
        m = RE_DATE.search(dt)
        if m:
            result['date'] = m.group()
            break

    # Vendor name
    vendor_parts = [w['text'] for w in fields['vendor']]
    # Filter out zebra noise
    vendor_parts = [p for p in vendor_parts if not RE_ZEBRA_NOISE.match(p) and p not in ('+',)]
    # Remove leading '+' artifact
    if vendor_parts and vendor_parts[0].startswith('+'):
        vendor_parts[0] = vendor_parts[0].lstrip('+')
    vendor_name = ' '.join(vendor_parts).strip()
    if vendor_name:
        result['vendor'] = vendor_name

    # Fd-Objt — may also contain "Cancelled"
    fd_texts = [w['text'] for w in fields['fd_objt']]
    cancelled = False
    fd_objt = None
    for ft in fd_texts:
        if 'cancel' in ft.lower() or 'void' in ft.lower():
            cancelled = True
        elif RE_FD_OBJT.match(ft):
            fd_objt = ft
    if fd_objt:
        result['fd_objt'] = fd_objt
    if cancelled:
        result['cancelled'] = True

    # Expensed Amount
    exp_texts = [w['text'] for w in fields['exp_amt']]
    for et in exp_texts:
        amt = parse_amount(et)
        if amt is not None:
            result['exp_amt'] = amt
            break

    # Check Amount
    chk_texts = [w['text'] for w in fields['check_amt']]
    for ct in chk_texts:
        amt = parse_amount(ct)
        if amt is not None:
            result['check_amt'] = amt
            break

    return result


def is_data_page(row_fields_list):
    """Determine if a page contains check data (vs cover letter or summary)."""
    check_count = sum(1 for rf in row_fields_list if 'check_num' in rf)
    return check_count >= 1


def is_summary_section(row_fields_list, row_idx):
    """Check if we've hit the summary section ('Total Number of Checks')."""
    for rf in row_fields_list[row_idx:]:
        vendor = rf.get('vendor', '')
        if 'Total Number' in vendor or 'Fund Recap' in vendor:
            return True
    return False


def parse_page(img_path, page_num):
    """Parse a single page image. Returns list of check entry dicts."""
    words = get_word_boxes(img_path)
    rows = group_into_rows(words)
    row_fields = [extract_row_fields(row) for row in rows]

    if not is_data_page(row_fields):
        return []

    checks = []
    current_check = None

    for i, rf in enumerate(row_fields):
        # Skip header rows (contain "Check", "Number", "Date", "Fd-Objt" etc.)
        vendor = rf.get('vendor', '')
        if any(h in vendor for h in ['Pay to the Order', 'Fd-Objt', 'Number Date']):
            continue
        if vendor in ('Number', 'Date', 'Amount'):
            continue
        # Skip "Checks Dated" header
        if 'Checks Dated' in vendor or 'through' in vendor:
            continue
        # Skip ReqPay12a header
        if 'ReqPay12a' in vendor or 'Board Report' in vendor:
            continue
        # Skip footer/disclaimer text
        if 'preceding Checks' in vendor or 'Board of Trustees' in vendor:
            continue
        if 'ERP for California' in vendor:
            continue
        # Skip summary section
        if 'Total Number' in vendor or 'Fund Recap' in vendor:
            break
        if 'Cancel' == vendor.strip() or 'Reissue' == vendor.strip() or 'Net Issue' == vendor.strip():
            break
        # Skip page number lines
        if vendor.startswith('Page ') and 'of' in vendor:
            continue
        # Skip generated-by footer
        if 'Generated for' in vendor or 'San Francisco Unified' in vendor:
            continue

        has_check_num = 'check_num' in rf
        has_fd_objt = 'fd_objt' in rf
        is_cancelled = rf.get('cancelled', False)

        # "Cancelled on MM/DD/YYYY" detail line — skip it
        if 'Cancelled on' in vendor or (vendor.startswith('Cancelled') and 'on' in vendor):
            continue

        if has_check_num:
            # New check entry
            if current_check and current_check.get('check_number'):
                checks.append(current_check)

            current_check = {
                'check_number': rf['check_num'],
                'date': rf.get('date', ''),
                'vendor_name': rf.get('vendor', ''),
                'fund_object': rf.get('fd_objt', ''),
                'amount': 0.0,
                'cancelled': is_cancelled,
                'page': page_num,
                'sub_lines': [],
            }

            if is_cancelled:
                # Cancelled checks: amount is in check_amt or exp_amt
                amt = rf.get('check_amt') or rf.get('exp_amt', 0.0)
                current_check['amount'] = amt or 0.0
            elif has_fd_objt:
                # Single-line check with fund-object
                exp = rf.get('exp_amt', 0.0) or 0.0
                chk = rf.get('check_amt', 0.0) or 0.0
                if chk > 0:
                    current_check['amount'] = chk
                else:
                    current_check['amount'] = exp
                if exp > 0:
                    current_check['sub_lines'].append({
                        'fund_object': rf.get('fd_objt', ''),
                        'exp_amount': exp,
                    })
            else:
                # Check number line without fd-objt yet (unusual but possible)
                current_check['amount'] = rf.get('check_amt', 0.0) or rf.get('exp_amt', 0.0) or 0.0

        elif current_check and (has_fd_objt or rf.get('exp_amt') or rf.get('check_amt')):
            # Could be continuation OR a new check with zebra-eaten check number.
            # Heuristic: if this row has a vendor name that differs from current check,
            # and has fd-objt + amount, it's likely a new check whose number was lost.
            is_new_check = False
            if vendor and has_fd_objt and (rf.get('exp_amt') or rf.get('check_amt')):
                # Different vendor from current check = new check
                cur_vendor = current_check.get('vendor_name', '')
                if vendor and cur_vendor and not vendor.startswith(cur_vendor.split()[0]) and not cur_vendor.startswith(vendor.split()[0]):
                    is_new_check = True

            if is_new_check:
                # Save current check, start new one with unknown number
                if current_check and current_check.get('check_number'):
                    checks.append(current_check)
                amt = rf.get('check_amt') or rf.get('exp_amt', 0.0) or 0.0
                current_check = {
                    'check_number': '_MISSING_',
                    'date': rf.get('date', ''),
                    'vendor_name': vendor,
                    'fund_object': rf.get('fd_objt', ''),
                    'amount': amt,
                    'cancelled': is_cancelled,
                    'page': page_num,
                    'sub_lines': [],
                }
                if rf.get('exp_amt'):
                    current_check['sub_lines'].append({
                        'fund_object': rf.get('fd_objt', ''),
                        'exp_amount': rf['exp_amt'],
                    })
            else:
                # Genuine continuation line for current check
                if has_fd_objt and rf.get('exp_amt'):
                    current_check['sub_lines'].append({
                        'fund_object': rf['fd_objt'],
                        'exp_amount': rf['exp_amt'],
                    })
                # Check Amount on continuation means total for this check
                if rf.get('check_amt'):
                    current_check['amount'] = rf['check_amt']

        elif current_check and vendor and not has_check_num:
            # Vendor name continuation line (wraps to next line)
            # Only append if it looks like text, not noise
            if not RE_ZEBRA_NOISE.match(vendor) and len(vendor) > 1:
                current_check['vendor_name'] += ' ' + vendor

    # Don't forget the last check
    if current_check and current_check.get('check_number'):
        checks.append(current_check)

    return checks


def process_month(month):
    """Process all pages for a single month. Returns list of check dicts."""
    pdf_path = WARRANTS_DIR / f"sfusd_Board-Report-of-Checks-in-{month}.pdf"
    if not pdf_path.exists():
        print(f"  WARNING: {pdf_path.name} not found")
        return []

    print(f"\n  Processing {month}...")

    with tempfile.TemporaryDirectory() as tmpdir:
        page_images = pdf_to_images(pdf_path, tmpdir)
        print(f"    {len(page_images)} pages at {DPI} DPI")

        all_checks = []
        for img_path in page_images:
            # Extract page number from filename (page-01.png -> 1)
            pg_str = img_path.stem.split('-')[-1]
            page_num = int(pg_str)

            page_checks = parse_page(img_path, page_num)
            all_checks.extend(page_checks)

        print(f"    Extracted {len(all_checks)} check entries")

    return all_checks


def reconcile_amounts(checks):
    """
    For multi-line checks, ensure amount = check_amt (last line total).
    For single-line checks without check_amt, amount = exp_amt.
    """
    for check in checks:
        if check.get('cancelled'):
            continue

        sub_lines = check.get('sub_lines', [])
        if len(sub_lines) > 1:
            # Multi-line: amount should already be the check_amt from the last sub-line
            # But verify: if amount is 0 or missing, sum the sub-lines
            if not check['amount'] or check['amount'] == 0:
                check['amount'] = round(sum(sl.get('exp_amount', 0) for sl in sub_lines), 2)
        elif len(sub_lines) == 1:
            # Single-line: if amount is missing, use exp_amount
            if not check['amount'] or check['amount'] == 0:
                check['amount'] = sub_lines[0].get('exp_amount', 0)

    return checks


def infer_missing_check_numbers(checks):
    """
    For checks marked _MISSING_, try to infer the check number from gaps in the sequence.
    Checks are in page order, so a _MISSING_ between 0200000001 and 0200000003 is 0200000002.
    """
    missing_indices = [i for i, c in enumerate(checks) if c.get('check_number') == '_MISSING_']
    if not missing_indices:
        return checks

    for idx in missing_indices:
        # Find the nearest check numbers before and after
        before_num = None
        after_num = None
        before_prefix = None

        for j in range(idx - 1, -1, -1):
            cn = checks[j].get('check_number', '')
            m = re.match(r'^(\d{3})(\d{7})$', cn)
            if m:
                before_prefix = m.group(1)
                before_num = int(cn)
                break
            m2 = re.match(r'^DDP-(\d+)$', cn)
            if m2:
                before_prefix = 'DDP'
                before_num = int(m2.group(1))
                break

        for j in range(idx + 1, len(checks)):
            cn = checks[j].get('check_number', '')
            m = re.match(r'^(\d{3})(\d{7})$', cn)
            if m:
                after_num = int(cn)
                break
            m2 = re.match(r'^DDP-(\d+)$', cn)
            if m2:
                after_num = int(m2.group(1))
                break

        # If there's exactly a gap of 2 (one missing number), infer it
        if before_num is not None and after_num is not None:
            expected = before_num + 1
            if expected == after_num - 0:
                # The missing one IS before_num + 1 (gap between before and after is exactly 2)
                pass  # expected is already set
            if after_num - before_num == 2:
                if before_prefix == 'DDP':
                    checks[idx]['check_number'] = f"DDP-{str(expected).zfill(8)}"
                else:
                    checks[idx]['check_number'] = str(expected).zfill(10)
        elif before_num is not None:
            expected = before_num + 1
            if before_prefix == 'DDP':
                checks[idx]['check_number'] = f"DDP-{str(expected).zfill(8)}"
            else:
                checks[idx]['check_number'] = str(expected).zfill(10)

    still_missing = sum(1 for c in checks if c.get('check_number') == '_MISSING_')
    if still_missing:
        print(f"    WARNING: {still_missing} checks still have unknown numbers")

    return checks


def fix_missing_dates(checks):
    """Fill in missing dates from the previous check (dates are only printed when they change)."""
    last_date = ''
    for check in checks:
        if check.get('date'):
            last_date = check['date']
        else:
            check['date'] = last_date
    return checks


def assign_month(checks, month):
    """Add month field to all checks."""
    for check in checks:
        check['month'] = month
    return checks


def detect_check_gaps(checks):
    """Find gaps in sequential check numbers. Returns list of missing numbers."""
    # Group by prefix (020, 120, DDP)
    groups = defaultdict(list)
    for c in checks:
        cn = c.get('check_number', '')
        if cn.startswith('020') or cn.startswith('120'):
            groups[cn[:3]].append(int(cn))
        elif cn.startswith('DDP-'):
            groups['DDP'].append(int(cn.replace('DDP-', '')))

    missing = []
    for prefix, nums in groups.items():
        nums = sorted(set(nums))
        for i in range(len(nums) - 1):
            gap = nums[i + 1] - nums[i]
            if 1 < gap <= 20:  # Don't flag large jumps (different series/dates)
                for n in range(nums[i] + 1, nums[i + 1]):
                    if prefix == 'DDP':
                        missing.append(f"DDP-{str(n).zfill(8)}")
                    else:
                        missing.append(str(n).zfill(10))
    return missing


def compute_month_summary(month, checks):
    """Compute validation summary for a month."""
    active = [c for c in checks if not c.get('cancelled', False)]
    cancelled = [c for c in checks if c.get('cancelled', False)]

    gross_total = sum(c.get('amount', 0) for c in active)
    cancel_total = sum(c.get('amount', 0) for c in cancelled)
    net_total = gross_total  # Active checks already exclude cancelled amounts

    expected = COVER_LETTER_TOTALS.get(month, 0)
    pct_diff = abs(net_total - expected) / expected * 100 if expected else 0

    expected_counts = COVER_LETTER_COUNTS.get(month, {})
    gaps = detect_check_gaps(checks)

    # Count unique check numbers
    unique_check_nums = set(c.get('check_number', '') for c in checks)

    return {
        "ocr_gross_total": round(gross_total, 2),
        "ocr_cancel_total": round(cancel_total, 2),
        "ocr_net_total": round(net_total, 2),
        "cover_letter_total": expected,
        "difference": round(net_total - expected, 2),
        "pct_difference": round(pct_diff, 2),
        "active_check_count": len(active),
        "cancelled_check_count": len(cancelled),
        "unique_check_numbers": len(unique_check_nums),
        "expected_gross_checks": expected_counts.get("gross", 0),
        "expected_cancels": expected_counts.get("cancels", 0),
        "expected_net_checks": expected_counts.get("net", 0),
        "missing_check_numbers": gaps,
        "missing_check_count": len(gaps),
    }


def main():
    print("=" * 70)
    print("SFUSD Check Register — Tesseract OCR + Geometric Parser")
    print("=" * 70)

    all_checks = []
    monthly_summaries = {}

    for month in MONTHS:
        month_checks = process_month(month)
        month_checks = fix_missing_dates(month_checks)
        month_checks = infer_missing_check_numbers(month_checks)
        month_checks = reconcile_amounts(month_checks)
        month_checks = assign_month(month_checks, month)

        summary = compute_month_summary(month, month_checks)
        monthly_summaries[month] = summary
        all_checks.extend(month_checks)

        # Print summary
        print(f"\n    {month} SUMMARY:")
        print(f"      Active checks: {summary['active_check_count']}, "
              f"Cancelled: {summary['cancelled_check_count']}")
        print(f"      OCR total:     ${summary['ocr_net_total']:>14,.2f}")
        print(f"      Cover letter:  ${summary['cover_letter_total']:>14,.2f}")
        print(f"      Difference:    ${summary['difference']:>+14,.2f} ({summary['pct_difference']:.2f}%)")
        if summary['missing_check_count'] > 0:
            print(f"      Missing check #s: {summary['missing_check_count']}")

    # Strip sub_lines from output (internal use only)
    for c in all_checks:
        c.pop('sub_lines', None)

    # Build output matching v1 schema
    data = {
        "checks": all_checks,
        "monthly_totals": {
            month: {
                "ocr_total": monthly_summaries[month]["ocr_net_total"],
                "cover_letter_total": monthly_summaries[month]["cover_letter_total"],
                "difference": monthly_summaries[month]["difference"],
                "pct_difference": monthly_summaries[month]["pct_difference"],
                "check_count": monthly_summaries[month]["active_check_count"],
            }
            for month in MONTHS if month in monthly_summaries
        },
        "total_checks": len(all_checks),
        "grand_total": round(
            sum(c.get('amount', 0) for c in all_checks if not c.get('cancelled', False)), 2
        ),
    }

    # Save main data
    out_file = DATA_DIR / "check_register_v2.json"
    with open(out_file, "w") as f:
        json.dump(data, f, indent=2)
    print(f"\nSaved {out_file} ({len(all_checks)} checks)")

    # Save quality report
    quality = {
        "monthly_summaries": monthly_summaries,
        "overall": {
            "total_checks": len(all_checks),
            "active_checks": len([c for c in all_checks if not c.get('cancelled', False)]),
            "cancelled_checks": len([c for c in all_checks if c.get('cancelled', False)]),
            "grand_total_active": round(
                sum(c.get('amount', 0) for c in all_checks if not c.get('cancelled', False)), 2
            ),
            "grand_total_cancel": round(
                sum(c.get('amount', 0) for c in all_checks if c.get('cancelled', False)), 2
            ),
            "grand_total_net": data["grand_total"],
            "expected_grand_total": round(sum(COVER_LETTER_TOTALS.values()), 2),
            "overall_pct_difference": round(
                abs(data["grand_total"] - sum(COVER_LETTER_TOTALS.values()))
                / sum(COVER_LETTER_TOTALS.values()) * 100, 2
            ),
            "total_missing_check_numbers": sum(
                s["missing_check_count"] for s in monthly_summaries.values()
            ),
        },
    }

    quality_file = DATA_DIR / "check_register_v2_quality.json"
    with open(quality_file, "w") as f:
        json.dump(quality, f, indent=2)
    print(f"Saved {quality_file}")

    # Final reconciliation table
    print("\n" + "=" * 70)
    print("FINAL RECONCILIATION")
    print("=" * 70)
    print(f"{'Month':<12} {'OCR Total':>14} {'Cover Letter':>14} {'Diff':>12} {'%':>7}")
    print("-" * 60)
    for month in MONTHS:
        s = monthly_summaries.get(month, {})
        print(f"{month:<12} ${s.get('ocr_net_total', 0):>12,.2f} ${s.get('cover_letter_total', 0):>12,.2f} "
              f"${s.get('difference', 0):>+10,.2f} {s.get('pct_difference', 0):>6.2f}%")
    print("-" * 60)
    total_ocr = sum(s["ocr_net_total"] for s in monthly_summaries.values())
    total_expected = sum(COVER_LETTER_TOTALS.values())
    total_diff = total_ocr - total_expected
    total_pct = abs(total_diff) / total_expected * 100
    print(f"{'TOTAL':<12} ${total_ocr:>12,.2f} ${total_expected:>12,.2f} "
          f"${total_diff:>+10,.2f} {total_pct:>6.2f}%")
    print(f"\nTarget: <2% per month. "
          f"{'PASS' if all(s['pct_difference'] < 2 for s in monthly_summaries.values()) else 'NEEDS REVIEW'}")


if __name__ == "__main__":
    main()

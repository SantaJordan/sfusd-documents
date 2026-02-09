#!/usr/bin/env python3
"""
Re-OCR SFUSD Board Report of Checks using GPT-4o at 300 DPI.

Fixes from v1 (GPT-4o-mini @ 200 DPI):
  - GPT-4o for much better structured table extraction
  - 300 DPI for sharper text on scanned pages
  - 8192 max_tokens to avoid truncation on dense pages
  - Enhanced prompt handling multi-line entries, DDP checks, cancelled checks
  - Per-page validation with automatic retry at 400 DPI
  - Half-page splitting for pages that still fail after retry
  - Cancelled check handling (subtract from gross)

Output: data/check_register_v2.json + data/check_register_v2_quality.json
"""

import base64
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

# ---------------------------------------------------------------------------
# CONFIGURATION
# ---------------------------------------------------------------------------
BASE_DIR = Path("/Users/jordancrawford/Desktop/Claude Code/Erin/sfusd-documents")
WARRANTS_DIR = BASE_DIR / "spending-analysis" / "warrants"
DATA_DIR = BASE_DIR / "analysis" / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

MONTHS = ["July", "August", "September", "October", "November", "December"]

COVER_LETTER_TOTALS = {
    "July": 60523520.99,
    "August": 24700613.85,
    "September": 65280245.59,
    "October": 52194350.99,
    "November": 50948400.89,
    "December": 59059990.47,
}

# Cover letter check counts (gross checks - cancels + reissues = net)
# These are from the fund recap summary on the last page of each PDF
COVER_LETTER_COUNTS = {
    "July": {"gross": 1088, "cancels": 22, "reissues": 2, "net": 1066},
    "August": {"gross": 457, "cancels": 27, "reissues": 0, "net": 430},
    "September": {"gross": 1242, "cancels": 14, "reissues": 0, "net": 1228},
    "October": {"gross": 1122, "cancels": 11, "reissues": 0, "net": 1111},
    "November": {"gross": 1123, "cancels": 31, "reissues": 0, "net": 1092},
    "December": {"gross": 1296, "cancels": 20, "reissues": 0, "net": 1276},
}

MAX_WORKERS = 5  # GPT-4o has tighter rate limits than mini
DEFAULT_DPI = 300
RETRY_DPI = 400

OCR_PROMPT = """Extract ALL check/warrant entries from this scanned SFUSD Board Report of Checks page.

Each entry has: check number, date, vendor name, fund-object code, and dollar amount.

CRITICAL RULES:
1. Some checks span MULTIPLE LINES — one check number has several fund-object + amount rows beneath it.
   List each sub-line as a SEPARATE entry sharing the same check_number, date, and vendor_name.
2. Check numbers may be prefixed: "020000xxxx" (regular), "DDP-xxxx" (payroll deduction), "120000xxxx" (other).
   Preserve the FULL prefix exactly as printed.
3. CANCELLED checks are marked with asterisks (*) or the word "CANCEL"/"VOID".
   Set "cancelled": true for these. Still include the amount.
4. Include ALL entries — do not skip any rows even if they look like sub-totals or continuation lines.
5. The amount column is on the far right. Amounts may have commas and always have cents (e.g., 1,234.56).
6. Fund-object codes look like "01-5803" or "12-4300" (fund number dash object code).
7. If a row has no check number, it's a continuation of the previous check — use the same check_number.

Return ONLY valid JSON (no markdown code fences):
{"checks": [{"check_number": "020000123", "date": "MM/DD/YYYY", "vendor_name": "Vendor Name", "fund_object": "01-5803", "amount": 1234.56, "cancelled": false}]}

Rules for JSON: Use double quotes only. amount must be a number not a string. No trailing commas.
If the page has no check entries (e.g., cover letter, summary page), return {"checks": []}.
Preserve exact vendor name spelling from the document."""


def get_openai_client():
    """Initialize OpenAI client."""
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("ERROR: OPENAI_API_KEY not set.")
        sys.exit(1)
    from openai import OpenAI
    return OpenAI(api_key=api_key)


def pdf_to_images(pdf_path, dpi, tmpdir):
    """Convert PDF to PNG images at given DPI. Returns sorted list of image paths."""
    subprocess.run(
        ["pdftoppm", "-png", "-r", str(dpi), str(pdf_path), f"{tmpdir}/page"],
        check=True, capture_output=True,
    )
    return sorted(Path(tmpdir).glob("page-*.png"))


def read_image_b64(img_path):
    """Read image file and return base64 string."""
    with open(img_path, "rb") as f:
        return base64.b64encode(f.read()).decode()


def fix_json(raw):
    """Aggressively fix common JSON issues from GPT-4o output."""
    # Strip markdown fences
    raw = re.sub(r'^```(?:json)?\s*', '', raw)
    raw = re.sub(r'\s*```$', '', raw)
    # Fix trailing commas
    raw = re.sub(r',\s*}', '}', raw)
    raw = re.sub(r',\s*\]', ']', raw)
    # Replace single quotes with double quotes (but not inside strings like O'Brien)
    # Strategy: try parsing as-is first, then fix
    return raw


def parse_json_robust(raw):
    """Try multiple strategies to parse JSON from GPT-4o output."""
    raw = fix_json(raw)
    json_match = re.search(r'\{[\s\S]*\}', raw)
    if not json_match:
        return None

    text = json_match.group()

    # Strategy 1: Direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Strategy 2: Fix unescaped control characters inside strings
    # Replace literal tabs/newlines inside JSON strings
    text2 = re.sub(r'(?<=": ")([^"]*?)(?=")', lambda m: m.group(1).replace('\n', ' ').replace('\t', ' '), text)
    try:
        return json.loads(text2)
    except json.JSONDecodeError:
        pass

    # Strategy 3: Use ast.literal_eval after converting to Python-safe format
    # This handles single quotes, True/False vs true/false, etc.
    try:
        import ast
        text3 = text.replace('true', 'True').replace('false', 'False').replace('null', 'None')
        obj = ast.literal_eval(text3)
        # Convert back to proper JSON types
        return json.loads(json.dumps(obj))
    except (ValueError, SyntaxError):
        pass

    # Strategy 4: Try to extract individual check entries with regex
    # Last resort — extract check_number/amount pairs
    checks = []
    pattern = re.compile(
        r'"check_number"\s*:\s*"([^"]+)".*?'
        r'"date"\s*:\s*"([^"]*)".*?'
        r'"vendor_name"\s*:\s*"([^"]*)".*?'
        r'"fund_object"\s*:\s*"([^"]*)".*?'
        r'"amount"\s*:\s*([\d.,]+)',
        re.DOTALL
    )
    for m in pattern.finditer(text):
        try:
            amt = float(m.group(5).replace(",", ""))
            checks.append({
                "check_number": m.group(1),
                "date": m.group(2),
                "vendor_name": m.group(3),
                "fund_object": m.group(4),
                "amount": amt,
                "cancelled": False,
            })
        except ValueError:
            continue
    if checks:
        return {"checks": checks}

    return None


def ocr_single_image(client, img_b64, month, page_num, detail="high"):
    """OCR a single page image using GPT-4o. Returns list of check dicts."""
    for attempt in range(3):
        try:
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": [
                    {"type": "text", "text": OCR_PROMPT},
                    {"type": "image_url", "image_url": {
                        "url": f"data:image/png;base64,{img_b64}",
                        "detail": detail,
                    }},
                ]}],
                max_tokens=8192,
                temperature=0,
                response_format={"type": "json_object"},
            )
            raw = response.choices[0].message.content.strip()
            page_data = parse_json_robust(raw)
            if page_data is None:
                if attempt < 2:
                    print(f"      Retry {attempt+1} for {month} page {page_num}: could not parse JSON")
                    time.sleep(2 * (attempt + 1))
                    continue
                print(f"      FAILED to parse JSON for {month} page {page_num}")
                return []

            checks = page_data.get("checks", [])
            for c in checks:
                c["month"] = month
                c["page"] = page_num
                # Normalize amount
                if isinstance(c.get("amount"), str):
                    c["amount"] = float(c["amount"].replace(",", "").replace("$", ""))
                # Ensure cancelled field exists
                if "cancelled" not in c:
                    c["cancelled"] = False
            return checks
        except Exception as e:
            if attempt < 2:
                print(f"      Retry {attempt+1} for {month} page {page_num}: {e}")
                time.sleep(2 * (attempt + 1))
    print(f"      FAILED all 3 attempts for {month} page {page_num}")
    return []


def split_image_halves(img_b64):
    """Split a base64 image into top and bottom halves. Returns two base64 strings."""
    from PIL import Image
    import io
    img_bytes = base64.b64decode(img_b64)
    img = Image.open(io.BytesIO(img_bytes))
    w, h = img.size
    mid = h // 2
    # Add 5% overlap to avoid splitting a row
    overlap = int(h * 0.05)

    top = img.crop((0, 0, w, mid + overlap))
    bottom = img.crop((0, mid - overlap, w, h))

    def to_b64(pil_img):
        buf = io.BytesIO()
        pil_img.save(buf, format="PNG")
        return base64.b64encode(buf.getvalue()).decode()

    return to_b64(top), to_b64(bottom)


def deduplicate_checks(checks):
    """Remove duplicate check entries that might come from overlapping half-page OCR."""
    seen = set()
    deduped = []
    for c in checks:
        key = (c.get("check_number", ""), c.get("fund_object", ""), c.get("amount", 0))
        if key not in seen:
            seen.add(key)
            deduped.append(c)
    return deduped


def detect_check_gaps(checks):
    """Find gaps in sequential check numbers. Returns list of missing numbers."""
    # Extract numeric parts from check numbers
    regular_nums = []
    for c in checks:
        cn = c.get("check_number", "")
        # Regular checks: 020000xxxx or 120000xxxx
        m = re.match(r'^(\d{10})$', cn)
        if m:
            regular_nums.append(int(m.group(1)))

    if not regular_nums:
        return []

    regular_nums = sorted(set(regular_nums))
    missing = []
    for i in range(len(regular_nums) - 1):
        gap = regular_nums[i + 1] - regular_nums[i]
        if gap > 1 and gap <= 20:  # Don't flag large jumps (different series)
            for n in range(regular_nums[i] + 1, regular_nums[i + 1]):
                missing.append(str(n).zfill(10))
    return missing


def process_month(client, month):
    """Process all pages for a single month. Returns (checks, page_stats)."""
    pdf_path = WARRANTS_DIR / f"sfusd_Board-Report-of-Checks-in-{month}.pdf"
    if not pdf_path.exists():
        print(f"  WARNING: {pdf_path.name} not found")
        return [], []

    print(f"\n  Processing {month}...")
    page_stats = []

    with tempfile.TemporaryDirectory() as tmpdir:
        # First pass: 300 DPI
        page_images = pdf_to_images(pdf_path, DEFAULT_DPI, tmpdir)
        print(f"    {len(page_images)} pages at {DEFAULT_DPI} DPI -> sending to GPT-4o ({MAX_WORKERS} concurrent)...")

        # Read all images into memory
        page_data = []
        for i, img_path in enumerate(page_images):
            page_data.append({
                "img_b64": read_image_b64(img_path),
                "page_num": i + 1,
            })

        # Process concurrently
        all_checks = []
        done_count = 0

        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = {}
            for pd in page_data:
                f = executor.submit(
                    ocr_single_image, client, pd["img_b64"], month, pd["page_num"]
                )
                futures[f] = pd

            for future in as_completed(futures):
                pd = futures[future]
                page_checks = future.result()
                all_checks.extend(page_checks)
                done_count += 1

                page_stats.append({
                    "page": pd["page_num"],
                    "check_count": len(page_checks),
                    "total": round(sum(c.get("amount", 0) for c in page_checks), 2),
                    "dpi": DEFAULT_DPI,
                    "method": "full_page",
                })

                if done_count % 5 == 0 or done_count == len(page_images):
                    running_total = sum(c.get("amount", 0) for c in all_checks)
                    print(f"    {done_count}/{len(page_images)} pages done "
                          f"({len(all_checks)} checks, ${running_total:,.0f})")

    return all_checks, page_stats


def retry_weak_pages(client, month, all_checks, page_stats):
    """Retry pages that seem to have missing data at 400 DPI or with half-page splitting."""
    pdf_path = WARRANTS_DIR / f"sfusd_Board-Report-of-Checks-in-{month}.pdf"

    # Identify pages with checks (non-cover/summary pages) to check for potential misses
    # Pages with very few checks compared to neighbors, or pages where check number gaps originate
    page_check_counts = defaultdict(int)
    page_checks_map = defaultdict(list)
    for c in all_checks:
        page_check_counts[c["page"]] += 1
        page_checks_map[c["page"]].append(c)

    # Detect check number gaps and map them to pages
    gaps = detect_check_gaps(all_checks)
    if not gaps:
        return all_checks, page_stats

    # Find which pages likely have the gaps (page just before or at the gap)
    all_check_nums = sorted(set(
        int(c["check_number"]) for c in all_checks
        if re.match(r'^\d{10}$', c.get("check_number", ""))
    ))

    pages_to_retry = set()
    for gap_num_str in gaps:
        gap_num = int(gap_num_str)
        # Find the page of the check just before and after the gap
        before_page = None
        after_page = None
        for c in all_checks:
            cn = c.get("check_number", "")
            if re.match(r'^\d{10}$', cn):
                n = int(cn)
                if n < gap_num and (before_page is None or n > int(before_page.get("check_number", "0"))):
                    before_page = c
                if n > gap_num and (after_page is None or n < int(after_page.get("check_number", "0"))):
                    after_page = c
        if before_page:
            pages_to_retry.add(before_page["page"])
        if after_page:
            pages_to_retry.add(after_page["page"])

    if not pages_to_retry:
        return all_checks, page_stats

    print(f"    Found {len(gaps)} check number gaps across {len(pages_to_retry)} pages — retrying at {RETRY_DPI} DPI...")

    with tempfile.TemporaryDirectory() as tmpdir:
        # Re-render at higher DPI
        page_images = pdf_to_images(pdf_path, RETRY_DPI, tmpdir)

        for page_num in sorted(pages_to_retry):
            if page_num > len(page_images):
                continue

            img_b64 = read_image_b64(page_images[page_num - 1])
            print(f"      Retrying page {page_num} at {RETRY_DPI} DPI...")

            retry_checks = ocr_single_image(client, img_b64, month, page_num)

            # Compare: does retry find more checks?
            original_page_checks = [c for c in all_checks if c["page"] == page_num]
            if len(retry_checks) > len(original_page_checks):
                print(f"        Improved: {len(original_page_checks)} -> {len(retry_checks)} checks")
                # Replace this page's checks
                all_checks = [c for c in all_checks if c["page"] != page_num] + retry_checks
                # Update stats
                for stat in page_stats:
                    if stat["page"] == page_num:
                        stat["dpi"] = RETRY_DPI
                        stat["method"] = "retry_high_dpi"
                        stat["check_count"] = len(retry_checks)
                        stat["total"] = round(sum(c.get("amount", 0) for c in retry_checks), 2)
            else:
                # Try half-page splitting
                print(f"        No improvement at {RETRY_DPI} DPI, trying half-page split...")
                top_b64, bottom_b64 = split_image_halves(img_b64)
                top_checks = ocr_single_image(client, top_b64, month, page_num)
                bottom_checks = ocr_single_image(client, bottom_b64, month, page_num)
                combined = deduplicate_checks(top_checks + bottom_checks)

                if len(combined) > len(original_page_checks):
                    print(f"        Half-page improved: {len(original_page_checks)} -> {len(combined)} checks")
                    all_checks = [c for c in all_checks if c["page"] != page_num] + combined
                    for stat in page_stats:
                        if stat["page"] == page_num:
                            stat["dpi"] = RETRY_DPI
                            stat["method"] = "half_page_split"
                            stat["check_count"] = len(combined)
                            stat["total"] = round(sum(c.get("amount", 0) for c in combined), 2)
                else:
                    print(f"        No improvement from split either ({len(combined)} checks)")

    return all_checks, page_stats


def compute_month_summary(month, checks, page_stats):
    """Compute validation summary for a month."""
    active_checks = [c for c in checks if not c.get("cancelled", False)]
    cancelled_checks = [c for c in checks if c.get("cancelled", False)]

    gross_total = sum(c.get("amount", 0) for c in active_checks)
    cancel_total = sum(c.get("amount", 0) for c in cancelled_checks)
    net_total = gross_total - cancel_total

    expected = COVER_LETTER_TOTALS.get(month, 0)
    pct_diff = abs(net_total - expected) / expected * 100 if expected else 0

    expected_counts = COVER_LETTER_COUNTS.get(month, {})
    gaps = detect_check_gaps(checks)

    return {
        "ocr_gross_total": round(gross_total, 2),
        "ocr_cancel_total": round(cancel_total, 2),
        "ocr_net_total": round(net_total, 2),
        "cover_letter_total": expected,
        "difference": round(net_total - expected, 2),
        "pct_difference": round(pct_diff, 2),
        "active_check_count": len(active_checks),
        "cancelled_check_count": len(cancelled_checks),
        "unique_check_numbers": len(set(c.get("check_number", "") for c in checks)),
        "expected_gross_checks": expected_counts.get("gross", 0),
        "expected_cancels": expected_counts.get("cancels", 0),
        "expected_net_checks": expected_counts.get("net", 0),
        "missing_check_numbers": gaps,
        "missing_check_count": len(gaps),
        "pages_processed": len(page_stats),
        "pages_retried": len([s for s in page_stats if s.get("method") != "full_page"]),
    }


def main():
    print("=" * 70)
    print("SFUSD Check Register Re-OCR — GPT-4o @ 300 DPI")
    print("=" * 70)

    client = get_openai_client()

    all_checks = []
    monthly_summaries = {}
    all_page_stats = {}

    for month in MONTHS:
        month_checks, page_stats = process_month(client, month)

        # Retry pages with detected gaps
        month_checks, page_stats = retry_weak_pages(client, month, month_checks, page_stats)

        summary = compute_month_summary(month, month_checks, page_stats)
        monthly_summaries[month] = summary
        all_page_stats[month] = page_stats
        all_checks.extend(month_checks)

        # Print summary
        print(f"\n    {month} SUMMARY:")
        print(f"      Active checks: {summary['active_check_count']}, "
              f"Cancelled: {summary['cancelled_check_count']}")
        print(f"      OCR net total: ${summary['ocr_net_total']:,.2f}")
        print(f"      Cover letter:  ${summary['cover_letter_total']:,.2f}")
        print(f"      Difference:    ${summary['difference']:+,.2f} ({summary['pct_difference']:.2f}%)")
        if summary['missing_check_count'] > 0:
            print(f"      Missing check #s: {summary['missing_check_count']}")

    # Build output
    grand_total_active = sum(c.get("amount", 0) for c in all_checks if not c.get("cancelled", False))
    grand_total_cancel = sum(c.get("amount", 0) for c in all_checks if c.get("cancelled", False))

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
        "grand_total": round(grand_total_active - grand_total_cancel, 2),
    }

    # Save main data
    out_file = DATA_DIR / "check_register_v2.json"
    with open(out_file, "w") as f:
        json.dump(data, f, indent=2)
    print(f"\nSaved {out_file} ({len(all_checks)} checks)")

    # Save quality report
    quality = {
        "monthly_summaries": monthly_summaries,
        "page_stats": all_page_stats,
        "overall": {
            "total_checks": len(all_checks),
            "active_checks": len([c for c in all_checks if not c.get("cancelled", False)]),
            "cancelled_checks": len([c for c in all_checks if c.get("cancelled", False)]),
            "grand_total_active": round(grand_total_active, 2),
            "grand_total_cancel": round(grand_total_cancel, 2),
            "grand_total_net": round(grand_total_active - grand_total_cancel, 2),
            "expected_grand_total": round(sum(COVER_LETTER_TOTALS.values()), 2),
            "overall_pct_difference": round(
                abs((grand_total_active - grand_total_cancel) - sum(COVER_LETTER_TOTALS.values()))
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

    # Print final summary
    print("\n" + "=" * 70)
    print("FINAL RECONCILIATION")
    print("=" * 70)
    print(f"{'Month':<12} {'OCR Net':>14} {'Cover Letter':>14} {'Diff':>12} {'%':>7}")
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
    print(f"\nTarget: <2% per month. {'PASS' if all(s['pct_difference'] < 2 for s in monthly_summaries.values()) else 'NEEDS REVIEW'}")


if __name__ == "__main__":
    main()

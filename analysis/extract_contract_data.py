#!/usr/bin/env python3
"""
AI-powered contract data extraction using Claude Sonnet.
Reads downloaded PDFs and extracts structured pricing/terms data.
Uses Anthropic Python SDK with PDF support.
High concurrency for M4 MacBook Pro.
"""

import asyncio
import base64
import json
import os
import sys
import time
from pathlib import Path

import anthropic

# Load .env file if present
_env_path = Path(__file__).parent.parent / ".env"
if _env_path.exists():
    for line in _env_path.read_text().splitlines():
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
MODEL = "claude-sonnet-4-5-20250929"

DATA_DIR = Path(__file__).parent / "data"
CONTRACTS_DIR = Path(__file__).parent / "contracts"
MANIFEST_PATH = DATA_DIR / "download_manifest.json"
OUTPUT_PATH = DATA_DIR / "contract_extractions.json"

MAX_PDF_SIZE = 20 * 1024 * 1024  # 20MB for API
MAX_WORKERS = 25  # Concurrent API calls (Tier 4/5 key supports high throughput)
MIN_RELEVANCE = -1  # Process all PDFs with relevance >= this

EXTRACTION_PROMPT = """Extract all contract and pricing information from this document.
Return ONLY valid JSON (no markdown code fences) with the following structure:

{
  "has_contract_data": true/false,
  "contracts": [
    {
      "vendor_name": "exact vendor name",
      "district": "school district name",
      "contract_type": "Professional Services Agreement / Purchase Order / etc.",
      "total_value": 0,
      "term_start": "YYYY-MM-DD or null",
      "term_end": "YYYY-MM-DD or null",
      "rates": {"role_or_description": dollar_amount, ...},
      "rate_type": "hourly / annual / per_unit / fixed / etc.",
      "scope": "brief description of services",
      "approval_date": "YYYY-MM-DD or null",
      "competitive_bid": true/false/null,
      "sole_source": true/false/null,
      "renewal_terms": "description or null",
      "amendments": ["list of amendments if any"],
      "key_terms": ["notable contract terms"],
      "not_to_exceed": 0
    }
  ]
}

IMPORTANT:
- If the document is a board agenda packet, extract data for ALL vendor contracts mentioned
- Extract EVERY dollar amount, rate, and fee you can find
- For hourly rates, list each role/level separately (e.g., "senior_consultant": 285)
- If this is just meeting minutes with no contract details, set has_contract_data to false
- total_value should be a number (not a string), 0 if unknown
- not_to_exceed should be a number, 0 if not specified
- Be precise with district names - use full official names"""


CONTRACT_KEYWORDS = [
    'contract', 'agreement', 'rfp', 'proposal', 'bid', 'rate', 'pricing',
    'cost', 'nte', 'amendment', 'award', 'sow', 'order form', 'service',
    'staffing', 'consulting', 'warrant', 'purchase', 'procurement',
]


def score_relevance(path_str, url):
    """Score how likely a PDF is to contain contract/pricing data."""
    fname = path_str.split('/')[-1].lower()
    url_lower = url.lower()
    score = 0

    for kw in CONTRACT_KEYWORDS:
        if kw in fname:
            score += 2

    if 'boarddocs.com' in url_lower:
        score += 3
    if 'legistar.com' in url_lower:
        score += 2
    if 'contract' in url_lower or 'rfp' in url_lower:
        score += 2

    noise_keywords = ['990', 'annual-report', 'yearbook', 'newsletter', 'handbook',
                      'employee-handbook', 'guidebook', 'case-study', 'casestudy',
                      'user-handbook', 'press_release']
    for nk in noise_keywords:
        if nk in fname:
            score -= 3

    if '/sfusd/' in path_str:
        score += 5

    return score


def load_manifest():
    """Load download manifest to know which PDFs to process."""
    if not MANIFEST_PATH.exists():
        print("ERROR: No download manifest found. Run download_contracts.py first.")
        sys.exit(1)

    with open(MANIFEST_PATH) as f:
        manifest = json.load(f)

    downloaded = {}
    for url, entry in manifest.items():
        if entry.get("status") == "downloaded" and entry.get("path"):
            path = Path(entry["path"])
            if path.exists() and path.stat().st_size > 1000:
                entry["_relevance_score"] = score_relevance(entry["path"], url)
                downloaded[url] = entry

    return downloaded


def extract_text_from_pdf(pdf_path, max_chars=50000):
    """Extract text from PDF using pdfplumber (fallback for large PDFs)."""
    import pdfplumber
    text_parts = []
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
                # Also extract tables
                tables = page.extract_tables()
                for table in tables:
                    for row in table:
                        if row:
                            text_parts.append(" | ".join(str(cell or "") for cell in row))
                if sum(len(t) for t in text_parts) > max_chars:
                    break
    except Exception as e:
        return f"[PDF text extraction failed: {e}]"

    full_text = "\n".join(text_parts)
    if len(full_text) > max_chars:
        full_text = full_text[:max_chars] + "\n[...truncated...]"
    return full_text


def extract_from_pdf_sync(pdf_path, vendor_hint, district_hint):
    """Send PDF to Claude for extraction (sync version for thread pool).
    Falls back to text extraction for oversized or problematic PDFs."""
    path = Path(pdf_path)
    if not path.exists():
        return {"error": f"File not found: {pdf_path}", "has_contract_data": False}

    file_size = path.stat().st_size

    with open(path, 'rb') as f:
        pdf_bytes = f.read()

    if pdf_bytes[:5] != b'%PDF-':
        return {"error": "Not a valid PDF file", "has_contract_data": False}

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    context = f"This PDF may be related to vendor '{vendor_hint}'"
    if district_hint and district_hint != "unknown":
        context += f" and school district '{district_hint}'"

    # Choose strategy: native PDF for small files, text extraction for large ones
    use_text_fallback = file_size > MAX_PDF_SIZE

    try:
        if use_text_fallback:
            # Extract text and send as plain text (works for any size)
            extracted_text = extract_text_from_pdf(path)
            if not extracted_text or len(extracted_text) < 100:
                return {"error": "Could not extract text from large PDF", "has_contract_data": False}

            message = client.messages.create(
                model=MODEL,
                max_tokens=4096,
                messages=[{
                    "role": "user",
                    "content": f"{context}\n\nThe following is text extracted from a PDF document:\n\n{extracted_text}\n\n{EXTRACTION_PROMPT}"
                }]
            )
        else:
            # Send native PDF (better for scanned docs, tables, etc.)
            pdf_b64 = base64.standard_b64encode(pdf_bytes).decode("utf-8")
            message = client.messages.create(
                model=MODEL,
                max_tokens=4096,
                messages=[{
                    "role": "user",
                    "content": [
                        {
                            "type": "document",
                            "source": {
                                "type": "base64",
                                "media_type": "application/pdf",
                                "data": pdf_b64,
                            },
                        },
                        {
                            "type": "text",
                            "text": f"{context}\n\n{EXTRACTION_PROMPT}",
                        }
                    ]
                }]
            )

        response_text = message.content[0].text.strip()
        if response_text.startswith("```"):
            response_text = response_text.split("\n", 1)[1]
            if response_text.endswith("```"):
                response_text = response_text[:-3]
            response_text = response_text.strip()

        # Handle cases where model returns multiple JSON objects or extra text
        try:
            result = json.loads(response_text)
        except json.JSONDecodeError:
            # Try to find the first complete JSON object
            depth = 0
            start = response_text.index('{')
            for i, c in enumerate(response_text[start:], start):
                if c == '{':
                    depth += 1
                elif c == '}':
                    depth -= 1
                    if depth == 0:
                        result = json.loads(response_text[start:i+1])
                        break
            else:
                raise json.JSONDecodeError("Could not find complete JSON", response_text, 0)
        result["_source_file"] = str(pdf_path)
        result["_file_size"] = file_size
        result["_tokens_used"] = {
            "input": message.usage.input_tokens,
            "output": message.usage.output_tokens,
        }
        return result

    except json.JSONDecodeError as e:
        return {
            "error": f"JSON parse error: {e}",
            "raw_response": response_text[:500] if 'response_text' in dir() else "",
            "_source_file": str(pdf_path),
            "has_contract_data": False,
        }
    except anthropic.APIError as e:
        # Retry with text fallback if native PDF failed (400 = too many pages, etc.)
        if not use_text_fallback and ("400" in str(e) or "invalid" in str(e).lower()):
            try:
                extracted_text = extract_text_from_pdf(path)
                if extracted_text and len(extracted_text) >= 100:
                    message = client.messages.create(
                        model=MODEL,
                        max_tokens=4096,
                        messages=[{
                            "role": "user",
                            "content": f"{context}\n\nText extracted from a PDF:\n\n{extracted_text}\n\n{EXTRACTION_PROMPT}"
                        }]
                    )
                    response_text = message.content[0].text.strip()
                    if response_text.startswith("```"):
                        response_text = response_text.split("\n", 1)[1]
                        if response_text.endswith("```"):
                            response_text = response_text[:-3]
                        response_text = response_text.strip()
                    result = json.loads(response_text)
                    result["_source_file"] = str(pdf_path)
                    result["_file_size"] = file_size
                    result["_method"] = "text_fallback_after_api_error"
                    result["_tokens_used"] = {
                        "input": message.usage.input_tokens,
                        "output": message.usage.output_tokens,
                    }
                    return result
            except Exception:
                pass  # Fall through to original error
        return {
            "error": f"API error: {e}",
            "_source_file": str(pdf_path),
            "has_contract_data": False,
        }
    except Exception as e:
        return {
            "error": f"Unexpected error: {e}",
            "_source_file": str(pdf_path),
            "has_contract_data": False,
        }


def main():
    if not ANTHROPIC_API_KEY:
        print("ERROR: ANTHROPIC_API_KEY not set", file=sys.stderr)
        sys.exit(1)

    manifest = load_manifest()
    print(f"Found {len(manifest)} downloaded PDFs", flush=True)

    # Load existing extractions (for resume)
    extractions = {}
    if OUTPUT_PATH.exists():
        with open(OUTPUT_PATH) as f:
            extractions = json.load(f)
        print(f"Resuming: {len(extractions)} PDFs already extracted", flush=True)

    # Filter and sort by relevance
    to_process = []
    for url, entry in manifest.items():
        if url not in extractions and entry.get("_relevance_score", 0) >= MIN_RELEVANCE:
            to_process.append((url, entry))

    # Sort by relevance (highest first), then by file size (smaller first for speed)
    to_process.sort(key=lambda x: (-x[1].get("_relevance_score", 0), Path(x[1]["path"]).stat().st_size))

    print(f"To process: {len(to_process)} PDFs (min relevance: {MIN_RELEVANCE})", flush=True)
    if not to_process:
        print("Nothing to do.", flush=True)
        return

    total_size_mb = sum(Path(e["path"]).stat().st_size for _, e in to_process
                        if Path(e["path"]).exists()) / (1024 * 1024)
    print(f"Total PDF size: {total_size_mb:.1f}MB", flush=True)
    print(f"Estimated cost: ~${len(to_process) * 0.05:.2f}", flush=True)
    print(f"Concurrency: {MAX_WORKERS} parallel API calls", flush=True)

    # Process with ThreadPoolExecutor
    stats = {"success": 0, "no_data": 0, "error": 0, "total_contracts": 0}
    total_input_tokens = 0
    total_output_tokens = 0
    start_time = time.time()

    from concurrent.futures import ThreadPoolExecutor, as_completed

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {}
        for url, entry in to_process:
            pdf_path = entry["path"]
            vendor = entry.get("vendor", "unknown")
            district = entry.get("district", "unknown")
            future = executor.submit(extract_from_pdf_sync, pdf_path, vendor, district)
            futures[future] = (url, entry)

        for i, future in enumerate(as_completed(futures)):
            url, entry = futures[future]
            vendor = entry.get("vendor", "?")[:35]
            district = entry.get("district", "?")

            try:
                result = future.result()
            except Exception as e:
                result = {"error": str(e), "has_contract_data": False}

            if result.get("error"):
                stats["error"] += 1
                print(f"  [{i+1}/{len(to_process)}] ERR: {vendor} - {result['error'][:80]}", flush=True)
            elif not result.get("has_contract_data", False):
                stats["no_data"] += 1
                if (i + 1) % 20 == 0:
                    print(f"  [{i+1}/{len(to_process)}] no data: {vendor}", flush=True)
            else:
                contracts = result.get("contracts", [])
                stats["success"] += 1
                stats["total_contracts"] += len(contracts)
                for c in contracts:
                    val = c.get("total_value") or c.get("not_to_exceed") or 0
                    rates = c.get("rates", {})
                    rate_preview = ""
                    if rates:
                        first_key = list(rates.keys())[0]
                        rate_preview = f" | {first_key}: ${rates[first_key]}" if isinstance(rates[first_key], (int, float)) else ""
                    print(f"  [{i+1}/{len(to_process)}] FOUND: {c.get('vendor_name', vendor)[:30]} @ {c.get('district', '?')}"
                          f" = ${val:,.0f}{rate_preview}", flush=True)

            tokens = result.get("_tokens_used", {})
            total_input_tokens += tokens.get("input", 0)
            total_output_tokens += tokens.get("output", 0)

            extractions[url] = result

            # Save every 10 extractions
            if (i + 1) % 10 == 0:
                with open(OUTPUT_PATH, 'w') as f:
                    json.dump(extractions, f, indent=2)
                elapsed = time.time() - start_time
                rate = (i + 1) / elapsed * 60
                print(f"  --- {i+1}/{len(to_process)} | {stats['success']} with data, "
                      f"{stats['total_contracts']} contracts | {rate:.0f}/min ---", flush=True)

    # Final save
    with open(OUTPUT_PATH, 'w') as f:
        json.dump(extractions, f, indent=2)

    elapsed = time.time() - start_time
    est_cost = (total_input_tokens * 3 / 1_000_000) + (total_output_tokens * 15 / 1_000_000)

    print(f"\n{'='*60}", flush=True)
    print(f"EXTRACTION COMPLETE ({elapsed:.0f}s)", flush=True)
    print(f"{'='*60}", flush=True)
    print(f"PDFs processed: {len(to_process)}", flush=True)
    print(f"With contract data: {stats['success']}", flush=True)
    print(f"No contract data: {stats['no_data']}", flush=True)
    print(f"Errors: {stats['error']}", flush=True)
    print(f"Total contracts extracted: {stats['total_contracts']}", flush=True)
    print(f"Total tokens: {total_input_tokens:,} input, {total_output_tokens:,} output", flush=True)
    print(f"Estimated cost: ${est_cost:.2f}", flush=True)
    print(f"\nOutput saved to: {OUTPUT_PATH}", flush=True)


if __name__ == "__main__":
    main()

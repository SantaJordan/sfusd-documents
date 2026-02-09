#!/usr/bin/env python3
"""
Find peer district contracts for SFUSD vendors using Exa API.
Searches for publicly available contracts, board approvals, and rate cards
for each vendor across all CA school districts.
Uses direct API calls per CLAUDE.md batch operations rule.
"""

import json
import os
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import urllib.request
import urllib.error

# Load .env file if present
_env_path = Path(__file__).parent.parent / ".env"
if _env_path.exists():
    for line in _env_path.read_text().splitlines():
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

EXA_API_KEY = os.environ.get("EXA_API_KEY", "")
EXA_BASE = "https://api.exa.ai"

DATA_DIR = Path(__file__).parent / "data"
VENDOR_DB_PATH = DATA_DIR / "vendor_database.json"
EXISTING_RESULTS_PATH = DATA_DIR / "vendor_research_results.json"
OUTPUT_PATH = DATA_DIR / "peer_contracts.json"

# All vendors >= $500K, organized by tier
def load_vendors():
    """Load vendors from vendor_database.json, filtered to >= $500K."""
    with open(VENDOR_DB_PATH) as f:
        db = json.load(f)

    vendors = {}
    for v in db["vendors"]:
        amt = v["amount"]
        if amt >= 500000:
            vendors[v["name"]] = amt

    # Categorize by tier
    tier1 = {k: v for k, v in vendors.items() if v >= 5000000}
    tier2 = {k: v for k, v in vendors.items() if 1000000 <= v < 5000000}
    tier3 = {k: v for k, v in vendors.items() if 500000 <= v < 1000000}

    print(f"Tier 1 ($5M+): {len(tier1)} vendors, ${sum(tier1.values()):,.0f}")
    print(f"Tier 2 ($1M-$5M): {len(tier2)} vendors, ${sum(tier2.values()):,.0f}")
    print(f"Tier 3 ($500K-$1M): {len(tier3)} vendors, ${sum(tier3.values()):,.0f}")
    print(f"Total: {len(vendors)} vendors")

    return tier1, tier2, tier3


def clean_vendor_name(name):
    """Clean vendor name for search queries."""
    clean = name
    for suffix in [", INC.", " INC.", ", LLC", " LLC", ", PBC", " PBC",
                   ", LP", " LP", " HOLDINGS", " SERVICES HOLDINGS"]:
        clean = clean.replace(suffix, "")
    clean = clean.replace(" DBA ", " ").replace("(USA)", "").replace("DIST.", "DISTRICT")
    clean = clean.replace("CTR.", "CENTER").replace("SVC", "SERVICE")
    clean = clean.rstrip(". ")
    return clean.strip()


def exa_search(query, num_results=10, search_type="auto", contents=True):
    """Direct Exa API search."""
    url = f"{EXA_BASE}/search"
    payload = {
        "query": query,
        "numResults": num_results,
        "useAutoprompt": True,
        "type": search_type,
    }
    if contents:
        payload["contents"] = {
            "text": {"maxCharacters": 1500},
            "highlights": {"numSentences": 5}
        }

    headers = {
        "x-api-key": EXA_API_KEY,
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    }

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        print(f"  HTTP {e.code}: {query[:60]}... -> {body[:200]}", file=sys.stderr)
        return {"results": []}
    except Exception as e:
        print(f"  Error: {query[:60]}... -> {e}", file=sys.stderr)
        return {"results": []}


def extract_amount(text):
    """Try to extract dollar amounts from text."""
    amounts = []
    # Match patterns like $1,234,567 or $1.2M or $500,000
    for m in re.finditer(r'\$[\d,]+(?:\.\d+)?(?:\s*(?:million|M))?', text):
        raw = m.group()
        try:
            if 'million' in raw.lower() or raw.endswith('M'):
                num = float(re.sub(r'[^\d.]', '', raw)) * 1_000_000
            else:
                num = float(raw.replace('$', '').replace(',', ''))
            if 1000 <= num <= 500_000_000:  # reasonable contract range
                amounts.append(num)
        except ValueError:
            pass
    return amounts


def classify_result(result, vendor_clean):
    """Classify a search result as SFUSD, peer district, or other."""
    url = result.get("url", "").lower()
    title = result.get("title", "").lower()
    text = result.get("text", "").lower()
    combined = f"{url} {title} {text}"

    # Check if SFUSD-related
    is_sfusd = any(x in combined for x in [
        "sfusd", "san francisco unified", "sf unified",
        "go.boarddocs.com/ca/sfusd"
    ])

    # Try to identify the district
    district = None
    district_patterns = {
        "LAUSD": ["lausd", "los angeles unified"],
        "Oakland USD": ["oakland unified", "ousd", "go.boarddocs.com/ca/ousd"],
        "Sacramento City USD": ["sacramento city unified", "scusd"],
        "San Jose USD": ["san jose unified"],
        "Fresno USD": ["fresno unified"],
        "Long Beach USD": ["long beach unified", "lbusd"],
        "San Diego USD": ["san diego unified", "sdusd"],
        "Elk Grove USD": ["elk grove unified"],
        "Santa Ana USD": ["santa ana unified"],
        "Stockton USD": ["stockton unified"],
        "Riverside USD": ["riverside unified"],
        "Bakersfield City SD": ["bakersfield city", "kern high"],
        "Compton USD": ["compton unified"],
        "Vallejo City USD": ["vallejo"],
        "West Contra Costa USD": ["west contra costa"],
        "Mt. Diablo USD": ["mt diablo", "mount diablo"],
        "San Bernardino USD": ["san bernardino unified"],
        "Pomona USD": ["pomona unified"],
        "Pasadena USD": ["pasadena unified"],
        "Berkeley USD": ["berkeley unified", "busd"],
        "Alameda USD": ["alameda unified"],
    }

    if is_sfusd:
        district = "SFUSD"
    else:
        for dist_name, patterns in district_patterns.items():
            if any(p in combined for p in patterns):
                district = dist_name
                break

    # Generic school district detection
    if not district and any(x in combined for x in [
        "school district", "unified school", "board of education",
        "boarddocs.com", "k-12", "k12"
    ]):
        # Try to extract district name from title
        for m in re.finditer(r'([A-Z][a-z]+(?: [A-Z][a-z]+)*)\s+(?:Unified|School District|USD)', text, re.IGNORECASE):
            district = m.group().strip()
            break
        if not district:
            district = "Unknown School District"

    # Extract amounts
    amounts = extract_amount(result.get("text", "") + " " + result.get("title", ""))

    # Check if it's a PDF
    is_pdf = url.endswith(".pdf") or "/files/" in url

    return {
        "url": result.get("url", ""),
        "title": result.get("title", ""),
        "district": district,
        "is_sfusd": is_sfusd,
        "is_pdf": is_pdf,
        "amounts_found": [f"${a:,.0f}" for a in amounts],
        "excerpt": (result.get("text", "") or "")[:500],
        "highlights": result.get("highlights", [])[:3],
    }


def search_vendor_contracts(vendor_name, amount):
    """Run 5 targeted searches for a single vendor's contracts."""
    clean = clean_vendor_name(vendor_name)
    print(f"  Searching: {vendor_name} (${amount:,.0f})")

    all_results = []
    seen_urls = set()

    queries = [
        # 1. All K-12 contracts (PDFs)
        f'"{clean}" contract school district filetype:pdf',
        # 2. Board approvals with amounts
        f'"{clean}" "board approved" OR "board agenda" K-12',
        # 3. Rate cards and pricing
        f'"{clean}" rate OR pricing OR "cost per" OR "hourly rate" school',
        # 4. BoardDocs specifically
        f'"{clean}" site:boarddocs.com contract',
        # 5. RFPs (competitive bids show market rates)
        f'"{clean}" RFP OR "request for proposal" school district',
    ]

    for i, query in enumerate(queries):
        try:
            resp = exa_search(query, num_results=10)
            results = resp.get("results", [])
            for r in results:
                url = r.get("url", "")
                if url and url not in seen_urls:
                    seen_urls.add(url)
                    classified = classify_result(r, clean)
                    all_results.append(classified)
            time.sleep(0.5)
        except Exception as e:
            print(f"    Query {i+1} failed: {e}", file=sys.stderr)

    # Separate SFUSD vs peer results
    sfusd_contracts = [r for r in all_results if r["is_sfusd"]]
    peer_contracts = [r for r in all_results if r["district"] and not r["is_sfusd"]]
    other_results = [r for r in all_results if not r["district"]]

    return {
        "vendor_name": vendor_name,
        "sfusd_amount": amount,
        "search_clean_name": clean,
        "total_results": len(all_results),
        "sfusd_contracts": sfusd_contracts,
        "peer_contracts": peer_contracts,
        "other_results": other_results,
        "pdf_urls": [r["url"] for r in all_results if r["is_pdf"]],
    }


def mine_existing_results():
    """Extract contract URLs from existing vendor_research_results.json."""
    if not EXISTING_RESULTS_PATH.exists():
        print("No existing results file found.")
        return {}

    with open(EXISTING_RESULTS_PATH) as f:
        data = json.load(f)

    mined = {}
    vendors = data.get("vendors", {})

    for vendor_name, vendor_data in vendors.items():
        sfusd = []
        peers = []
        pdfs = []

        for search_key, results in vendor_data.get("searches", {}).items():
            if not isinstance(results, list):
                continue
            for r in results:
                url = r.get("url", "")
                if not url:
                    continue

                is_pdf = url.endswith(".pdf") or "/files/" in url
                if is_pdf:
                    pdfs.append(url)

                text = f"{url} {r.get('title', '')} {r.get('text', '')}".lower()

                if any(x in text for x in ["sfusd", "san francisco unified"]):
                    sfusd.append({
                        "url": url,
                        "title": r.get("title", ""),
                        "is_pdf": is_pdf,
                        "excerpt": (r.get("text", "") or "")[:300],
                        "source": "existing_research"
                    })
                elif any(x in text for x in ["school district", "unified", "boarddocs"]):
                    peers.append({
                        "url": url,
                        "title": r.get("title", ""),
                        "is_pdf": is_pdf,
                        "excerpt": (r.get("text", "") or "")[:300],
                        "source": "existing_research"
                    })

        if sfusd or peers or pdfs:
            mined[vendor_name] = {
                "sfusd_from_existing": sfusd,
                "peers_from_existing": peers,
                "pdf_urls_from_existing": pdfs,
            }

    print(f"Mined {len(mined)} vendors from existing results")
    return mined


def run_searches(vendors_by_tier, existing_data):
    """Run searches for all vendors, tier by tier."""
    output = {}

    # Load existing output if resuming
    if OUTPUT_PATH.exists():
        with open(OUTPUT_PATH) as f:
            output = json.load(f)
        print(f"Resuming: {len(output)} vendors already processed")

    all_vendors = []
    for tier_name, tier_vendors in vendors_by_tier:
        for name, amount in sorted(tier_vendors.items(), key=lambda x: -x[1]):
            if name not in output:
                all_vendors.append((name, amount, tier_name))

    print(f"\n{len(all_vendors)} vendors to search ({len(output)} already done)")

    for i, (name, amount, tier) in enumerate(all_vendors):
        print(f"\n[{i+1}/{len(all_vendors)}] {tier}: {name}")

        result = search_vendor_contracts(name, amount)

        # Merge with existing mined data
        if name in existing_data:
            ex = existing_data[name]
            # Add existing SFUSD results (dedup by URL)
            existing_urls = {r["url"] for r in result["sfusd_contracts"]}
            for r in ex.get("sfusd_from_existing", []):
                if r["url"] not in existing_urls:
                    result["sfusd_contracts"].append(r)
                    existing_urls.add(r["url"])

            # Add existing peer results
            existing_urls = {r["url"] for r in result["peer_contracts"]}
            for r in ex.get("peers_from_existing", []):
                if r["url"] not in existing_urls:
                    result["peer_contracts"].append(r)
                    existing_urls.add(r["url"])

            # Add existing PDF URLs
            existing_pdfs = set(result["pdf_urls"])
            for url in ex.get("pdf_urls_from_existing", []):
                if url not in existing_pdfs:
                    result["pdf_urls"].append(url)
                    existing_pdfs.add(url)

        output[name] = result

        # Save after every vendor (resume-safe)
        with open(OUTPUT_PATH, 'w') as f:
            json.dump(output, f, indent=2)

        # Status update
        total_sfusd = sum(len(v.get("sfusd_contracts", [])) for v in output.values())
        total_peers = sum(len(v.get("peer_contracts", [])) for v in output.values())
        total_pdfs = sum(len(v.get("pdf_urls", [])) for v in output.values())
        print(f"  -> {len(result['sfusd_contracts'])} SFUSD, {len(result['peer_contracts'])} peers, {len(result['pdf_urls'])} PDFs")
        print(f"  Running totals: {total_sfusd} SFUSD, {total_peers} peer contracts, {total_pdfs} PDFs")

    return output


def print_summary(output):
    """Print final summary."""
    total_sfusd = sum(len(v.get("sfusd_contracts", [])) for v in output.values())
    total_peers = sum(len(v.get("peer_contracts", [])) for v in output.values())
    total_pdfs = sum(len(v.get("pdf_urls", [])) for v in output.values())

    vendors_with_peers = sum(1 for v in output.values() if v.get("peer_contracts"))
    vendors_with_sfusd = sum(1 for v in output.values() if v.get("sfusd_contracts"))

    print(f"\n{'='*60}")
    print(f"PEER CONTRACT SEARCH COMPLETE")
    print(f"{'='*60}")
    print(f"Vendors searched: {len(output)}")
    print(f"Vendors with SFUSD contracts found: {vendors_with_sfusd}")
    print(f"Vendors with peer district contracts: {vendors_with_peers}")
    print(f"Total SFUSD contract refs: {total_sfusd}")
    print(f"Total peer contract refs: {total_peers}")
    print(f"Total PDF URLs: {total_pdfs}")

    # Top vendors by peer contract count
    by_peers = sorted(output.items(), key=lambda x: len(x[1].get("peer_contracts", [])), reverse=True)
    print(f"\nTop vendors by peer contracts found:")
    for name, data in by_peers[:15]:
        pc = len(data.get("peer_contracts", []))
        if pc > 0:
            districts = set(r.get("district", "?") for r in data["peer_contracts"])
            print(f"  {name}: {pc} contracts across {len(districts)} districts")


def main():
    if not EXA_API_KEY:
        print("ERROR: EXA_API_KEY not set", file=sys.stderr)
        sys.exit(1)

    # Load vendor tiers
    tier1, tier2, tier3 = load_vendors()

    # Mine existing research results first
    existing_data = mine_existing_results()

    # Run searches tier by tier
    tiers = [
        ("Tier 1 ($5M+)", tier1),
        ("Tier 2 ($1M-$5M)", tier2),
        ("Tier 3 ($500K-$1M)", tier3),
    ]

    output = run_searches(tiers, existing_data)
    print_summary(output)

    print(f"\nOutput saved to: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()

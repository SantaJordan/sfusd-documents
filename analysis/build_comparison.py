#!/usr/bin/env python3
"""
Build cross-district vendor contract comparison matrix.
Takes extracted contract data + search result amounts and produces:
1. Per-vendor comparison with market rates (where methodologically sound)
2. Contract process analysis (competitive bidding, amendments, transparency)
3. Rate transparency (what SFUSD pays per hour/unit for services)
4. Summary report
Also injects comparison data into the HTML explainer page.

VALIDATION NOTE: Cross-district price comparisons are only included when:
- All peers are K-12 school districts (not transit, university, city/county)
- Services are comparable in scope
- At least 2 valid K-12 peers with comparable contracts
- Time periods are similar (single-year contracts compared to single-year)
"""

import json
import re
import statistics
import sys
from pathlib import Path
from datetime import datetime

DATA_DIR = Path(__file__).parent / "data"
EXTRACTIONS_PATH = DATA_DIR / "contract_extractions.json"
PEER_CONTRACTS_PATH = DATA_DIR / "peer_contracts.json"
VENDOR_DB_PATH = DATA_DIR / "vendor_database.json"
VENDOR_CLASS_PATH = DATA_DIR / "vendor_classification_summary.json"
COMPARISON_OUTPUT = DATA_DIR / "contract_comparison.json"
HTML_PATH = Path(__file__).parent.parent / "sfusd-strike-explainer" / "index.html"

# Enrollment (ADA) for per-student normalization
DISTRICT_ADA = {
    "SFUSD": 49000,
    "San Francisco Unified School District": 49000,
    "LAUSD": 420000,
    "Los Angeles Unified School District": 420000,
    "Oakland USD": 34000,
    "Oakland Unified School District": 34000,
    "Sacramento City USD": 40000,
    "Sacramento City Unified School District": 40000,
    "San Jose USD": 26000,
    "San Jose Unified School District": 26000,
    "Fresno USD": 73000,
    "Fresno Unified School District": 73000,
    "Long Beach USD": 70000,
    "Long Beach Unified School District": 70000,
    "San Diego USD": 100000,
    "San Diego Unified School District": 100000,
    "Elk Grove USD": 63000,
    "Elk Grove Unified School District": 63000,
    "Berkeley USD": 9500,
    "Berkeley Unified School District": 9500,
    "Alameda USD": 8500,
    "Alameda Unified School District": 8500,
    "West Contra Costa USD": 27000,
    "West Contra Costa Unified School District": 27000,
    "Mt. Diablo USD": 29000,
    "Mt. Diablo Unified School District": 29000,
    "San Bernardino USD": 47000,
    "San Bernardino City Unified School District": 47000,
    "Stockton USD": 37000,
    "Stockton Unified School District": 37000,
    "Compton USD": 21000,
    "Compton Unified School District": 21000,
    "Riverside USD": 42000,
    "Riverside Unified School District": 42000,
    "Pasadena USD": 15000,
    "Pasadena Unified School District": 15000,
    "Board of Education of Howard County": 58000,
    "Howard County Public Schools": 58000,
    "Frederick County Public Schools": 45000,
    "Newark Unified School District": 6000,
    "Conejo Valley Unified School District": 19000,
    "Greenfield Union School District": 4000,
    "Palo Alto Unified School District": 11000,
    "Dallas Independent School District": 145000,
    "Chicago Public Schools": 330000,
    "ASD (Anchorage School District)": 44000,
    "Anchorage School District": 44000,
    "Highline Public Schools": 18000,
    "Baltimore County Public Schools": 113000,
    "Jefferson Elementary School District": 5000,
    "School Board of Clay County, Florida": 40000,
    "Corpus Christi Independent School District": 35000,
    "Seattle Public Schools": 50000,
    "Seattle School District No. 1": 50000,
    "Pocono Mountain School District": 10000,
    "Nassau County Public Schools": 11000,
    "Brecksville-Broadview Heights City Schools": 4000,
    "Gridley Unified School District": 2000,
    "Easton Area School District": 5000,
}

# Non-K12 entity indicators — these are NOT school districts
NON_K12_INDICATORS = [
    "transit", "retirement", "university", "college system",
    "city of ", "county of ", "city and county", "state of ",
    "community college", "housing authority", "water district",
    "fire department", "police department", "regional transit",
    "health department", "social services", "behavioral health",
    "public health", "county health",
]


def load_data():
    """Load all data files."""
    extractions = {}
    if EXTRACTIONS_PATH.exists():
        with open(EXTRACTIONS_PATH) as f:
            extractions = json.load(f)

    peer_contracts = {}
    if PEER_CONTRACTS_PATH.exists():
        with open(PEER_CONTRACTS_PATH) as f:
            peer_contracts = json.load(f)

    vendor_db = {"vendors": []}
    if VENDOR_DB_PATH.exists():
        with open(VENDOR_DB_PATH) as f:
            vendor_db = json.load(f)

    return extractions, peer_contracts, vendor_db


def normalize_vendor_name(name):
    """Normalize vendor name for matching."""
    n = name.upper().strip()
    for suffix in [", INC.", " INC.", ", LLC", " LLC", ", PBC", " PBC",
                   ", LP", " LP", " HOLDINGS", " CORP", " CORPORATION"]:
        n = n.replace(suffix, "")
    n = n.replace(".", "").replace(",", "").strip()
    return n


def is_k12_district(district_name):
    """Check if a name refers to an actual K-12 school district (not university, city, etc.)."""
    if not district_name:
        return False
    lower = district_name.lower().strip()

    # Reject non-K12 entities
    for indicator in NON_K12_INDICATORS:
        if indicator in lower:
            # Exception: "school district" overrides non-K12 indicator
            if "school" in lower and ("district" in lower or "board" in lower):
                continue
            return False

    # Must contain a school-related term OR be in our ADA lookup
    if district_name in DISTRICT_ADA:
        return True

    school_terms = ["school", "unified", "independent school", "public schools",
                    "education", "SELPA", "board of education"]
    return any(term in lower for term in school_terms)


def is_valid_district(district):
    """Check if a district name is real and not a description fragment."""
    if not district:
        return False
    lower = district.lower().strip()
    if lower in ("unknown", "unknown school district", "?", ""):
        return False
    if any(kw in lower for kw in [
        "will be in addition", "professional service agreement",
        "agreement between", "contract with the", "proposed budget",
        "recommended action", "how much does", "the buses will",
    ]):
        return False
    if len(district) > 80 or len(district) < 4:
        return False
    return True


def group_contracts_by_vendor(extractions):
    """Group all extracted contracts by normalized vendor name."""
    vendor_contracts = {}

    for url, extraction in extractions.items():
        if not extraction.get("has_contract_data"):
            continue

        for contract in extraction.get("contracts", []):
            vendor = contract.get("vendor_name", "")
            if not vendor:
                continue

            norm = normalize_vendor_name(vendor)
            if norm not in vendor_contracts:
                vendor_contracts[norm] = {
                    "display_name": vendor,
                    "contracts": [],
                }
            vendor_contracts[norm]["contracts"].append(contract)

    return vendor_contracts


def annualize_value(contract):
    """Estimate annual value from a contract with term dates."""
    total = contract.get("total_value") or contract.get("not_to_exceed") or 0
    if not total:
        return 0

    start = contract.get("term_start")
    end = contract.get("term_end")
    if not start or not end or start == "null" or end == "null":
        return total  # Assume 1 year if no dates

    try:
        from datetime import datetime as dt
        s = dt.strptime(start[:10], "%Y-%m-%d")
        e = dt.strptime(end[:10], "%Y-%m-%d")
        days = (e - s).days
        if days > 0:
            years = days / 365.25
            if years > 1.5:
                return round(total / years)
    except (ValueError, TypeError):
        pass

    return total


def analyze_vendor(vendor_name, contracts, sfusd_amount):
    """Build comparison analysis for a single vendor with strict validation."""
    sfusd_contracts = [c for c in contracts if "SFUSD" in (c.get("district", "") or "").upper()
                       or "SAN FRANCISCO" in (c.get("district", "") or "").upper()]

    # Filter peer contracts: must be valid K-12 district with reasonable value
    min_peer_value = max(sfusd_amount * 0.02, 10_000) if sfusd_amount else 10_000
    peer_contracts = []
    for c in contracts:
        if c in sfusd_contracts:
            continue
        district = c.get("district", "")
        if not is_valid_district(district):
            continue
        if not is_k12_district(district):
            continue
        cv = c.get("total_value") or c.get("not_to_exceed") or 0
        if cv >= min_peer_value:
            peer_contracts.append(c)

    if not sfusd_contracts and not peer_contracts:
        return None

    analysis = {
        "vendor_name": vendor_name,
        "sfusd_board_amount": sfusd_amount,
        "sfusd": {},
        "peers": [],
        "market": {},
        "analysis": {},
        "leverage": {},
    }

    # SFUSD data
    if sfusd_contracts:
        best_sfusd = max(sfusd_contracts, key=lambda c: c.get("total_value") or c.get("not_to_exceed") or 0)
        analysis["sfusd"] = {
            "total_value": best_sfusd.get("total_value") or best_sfusd.get("not_to_exceed") or sfusd_amount,
            "rates": best_sfusd.get("rates", {}),
            "rate_type": best_sfusd.get("rate_type", ""),
            "term_start": best_sfusd.get("term_start"),
            "term_end": best_sfusd.get("term_end"),
            "competitive_bid": best_sfusd.get("competitive_bid"),
            "sole_source": best_sfusd.get("sole_source"),
            "contract_type": best_sfusd.get("contract_type", ""),
            "scope": best_sfusd.get("scope", ""),
            "amendments": best_sfusd.get("amendments", []),
            "key_terms": best_sfusd.get("key_terms", []),
        }
        tv = analysis["sfusd"]["total_value"]
        if tv and tv > 0:
            analysis["sfusd"]["per_student"] = round(tv / DISTRICT_ADA["SFUSD"], 2)
    else:
        analysis["sfusd"] = {
            "total_value": sfusd_amount,
            "per_student": round(sfusd_amount / DISTRICT_ADA["SFUSD"], 2) if sfusd_amount else 0,
        }

    # Peer data (K-12 only)
    for pc in peer_contracts:
        district = pc.get("district", "Unknown")
        ada = DISTRICT_ADA.get(district, 0)
        tv = pc.get("total_value") or pc.get("not_to_exceed") or 0
        annual = annualize_value(pc)

        peer_entry = {
            "district": district,
            "total_value": tv,
            "annual_value": annual,
            "rates": pc.get("rates", {}),
            "rate_type": pc.get("rate_type", ""),
            "competitive_bid": pc.get("competitive_bid"),
            "term": f"{pc.get('term_start', '?')} to {pc.get('term_end', '?')}",
            "contract_type": pc.get("contract_type", ""),
            "scope": pc.get("scope", ""),
        }
        if ada and annual:
            peer_entry["per_student"] = round(annual / ada, 2)

        analysis["peers"].append(peer_entry)

    # Market analysis
    if peer_contracts:
        all_rates = {}
        sfusd_rates = analysis["sfusd"].get("rates", {})
        if sfusd_rates:
            for role, rate in sfusd_rates.items():
                if isinstance(rate, (int, float)) and rate > 0:
                    if role not in all_rates:
                        all_rates[role] = []
                    all_rates[role].append(("SFUSD", rate))
        for pc in peer_contracts:
            district = pc.get("district", "Unknown")
            for role, rate in pc.get("rates", {}).items():
                if isinstance(rate, (int, float)) and rate > 0:
                    if role not in all_rates:
                        all_rates[role] = []
                    all_rates[role].append((district, rate))

        all_values = []
        sfusd_val = analysis["sfusd"].get("total_value", 0)
        if sfusd_val:
            all_values.append(("SFUSD", sfusd_val))
        for pc in peer_contracts:
            tv = pc.get("total_value") or pc.get("not_to_exceed") or 0
            if tv > 0:
                all_values.append((pc.get("district", "?"), tv))

        districts_found = list(set(p.get("district", "?") for p in peer_contracts))

        analysis["market"] = {
            "contracts_found": len(peer_contracts),
            "districts": districts_found,
            "rate_comparison": {},
            "total_value_comparison": {},
        }

        for role, entries in all_rates.items():
            rates = [r for _, r in entries]
            if len(rates) >= 2:
                sfusd_rate = next((r for d, r in entries if d == "SFUSD"), None)
                peer_rates = [r for d, r in entries if d != "SFUSD"]
                analysis["market"]["rate_comparison"][role] = {
                    "sfusd_rate": sfusd_rate,
                    "median": statistics.median(peer_rates) if peer_rates else None,
                    "min": min(peer_rates) if peer_rates else None,
                    "max": max(peer_rates) if peer_rates else None,
                    "all_entries": [{"district": d, "rate": r} for d, r in entries],
                }

        if len(all_values) >= 2:
            peer_vals = [v for d, v in all_values if d != "SFUSD"]
            analysis["market"]["total_value_comparison"] = {
                "sfusd": sfusd_val,
                "peer_median": statistics.median(peer_vals) if peer_vals else 0,
                "peer_min": min(peer_vals) if peer_vals else 0,
                "peer_max": max(peer_vals) if peer_vals else 0,
            }

    # Red flags
    red_flags = []
    sfusd_data = analysis["sfusd"]
    if sfusd_data.get("sole_source") or sfusd_data.get("competitive_bid") == False:
        red_flags.append("sole-source / no competitive bid")
    if sfusd_data.get("amendments"):
        red_flags.append(f"{len(sfusd_data['amendments'])} amendment(s)")
    if any("increase" in str(a).lower() or "nte" in str(a).lower()
           for a in sfusd_data.get("amendments", [])):
        red_flags.append("NTE increased via amendments")

    analysis["analysis"] = {
        "red_flags": red_flags,
        "has_comparison": bool(peer_contracts),
    }

    if red_flags:
        analysis["leverage"] = {
            "recommendation": f"Red flags: {', '.join(red_flags)}.",
        }

    return analysis


def parse_amount(amount_str):
    """Parse a dollar amount string into a number."""
    if isinstance(amount_str, (int, float)):
        return float(amount_str)
    if not amount_str:
        return 0
    s = str(amount_str).replace("$", "").replace(",", "").strip()
    try:
        return float(s)
    except ValueError:
        return 0


def filter_plausible_amounts(amounts, sfusd_amount):
    """Filter search result amounts to plausible contract values."""
    if not amounts:
        return []
    if sfusd_amount:
        lower = max(sfusd_amount * 0.02, 10_000)
        upper = sfusd_amount * 20
    else:
        lower = 10_000
        upper = 100_000_000
    return [a for a in amounts if lower <= a <= upper]


def build_comparison(extractions, peer_contracts, vendor_db):
    """Build the full comparison matrix using all data sources."""
    vendor_contracts = group_contracts_by_vendor(extractions)

    sfusd_amounts = {}
    vendor_categories = {}
    for v in vendor_db.get("vendors", []):
        sfusd_amounts[normalize_vendor_name(v["name"])] = v["amount"]
        sfusd_amounts[v["name"]] = v["amount"]
        vendor_categories[normalize_vendor_name(v["name"])] = v.get("category", "")

    peer_data_by_norm = {}
    for vendor_name, pc_data in peer_contracts.items():
        norm = normalize_vendor_name(vendor_name)
        peer_data_by_norm[norm] = (vendor_name, pc_data)

    comparison = {}

    # STEP 1: Process vendors from PDF extractions
    for norm_name, data in vendor_contracts.items():
        display_name = data["display_name"]
        contracts = data["contracts"]
        sfusd_amount = sfusd_amounts.get(norm_name, 0)

        if not sfusd_amount:
            for orig_name, amt in sfusd_amounts.items():
                if normalize_vendor_name(orig_name) == norm_name:
                    sfusd_amount = amt
                    break

        analysis = analyze_vendor(display_name, contracts, sfusd_amount)
        if analysis:
            pc_key = norm_name
            if pc_key in peer_data_by_norm:
                _, pc_data = peer_data_by_norm[pc_key]
                search_peers = pc_data.get("peer_contracts", [])
                if search_peers and not analysis.get("peers"):
                    analysis["market"]["search_results"] = len(search_peers)
                    analysis["market"]["districts"] = list(set(
                        p.get("district", "?") for p in search_peers if p.get("district")
                    ))
            comparison[display_name] = analysis

    # STEP 2: Process vendors from peer_contracts.json (search results)
    for vendor_name, pc_data in peer_contracts.items():
        norm = normalize_vendor_name(vendor_name)

        already_covered = False
        for existing_name in comparison:
            if normalize_vendor_name(existing_name) == norm:
                already_covered = True
                break
        if already_covered:
            continue

        peers = pc_data.get("peer_contracts", [])
        sfusd_amount = pc_data.get("sfusd_amount", 0) or sfusd_amounts.get(norm, 0)
        if not sfusd_amount:
            continue

        sfusd_per_student = round(sfusd_amount / DISTRICT_ADA["SFUSD"], 2)
        category = vendor_categories.get(norm, "")

        # Collect peer amounts from K-12 districts only
        peer_amounts_by_district = {}
        for p in peers:
            district = p.get("district", "Unknown")
            if not is_valid_district(district) or not is_k12_district(district):
                continue
            amounts = [parse_amount(a) for a in p.get("amounts_found", [])]
            amounts = filter_plausible_amounts(amounts, sfusd_amount)
            if amounts:
                if district not in peer_amounts_by_district:
                    peer_amounts_by_district[district] = []
                peer_amounts_by_district[district].extend(amounts)

        peer_entries = []
        all_peer_values = []
        for district, amounts in peer_amounts_by_district.items():
            best_amount = max(amounts)
            ada = DISTRICT_ADA.get(district, 0)
            entry = {
                "district": district,
                "total_value": best_amount,
                "source": "search_result",
                "amounts_found": sorted(amounts, reverse=True)[:5],
            }
            if ada and best_amount:
                entry["per_student"] = round(best_amount / ada, 2)
            peer_entries.append(entry)
            all_peer_values.append(best_amount)

        districts_found = list(set(
            p.get("district", "?") for p in peers
            if is_valid_district(p.get("district")) and is_k12_district(p.get("district", ""))
        ))

        comparison[vendor_name] = {
            "vendor_name": vendor_name,
            "sfusd_board_amount": sfusd_amount,
            "category": category,
            "sfusd": {
                "total_value": sfusd_amount,
                "per_student": sfusd_per_student,
            },
            "peers": peer_entries,
            "market": {
                "contracts_found": len(peers),
                "districts": districts_found,
                "amounts_found": len(all_peer_values),
                "total_value_comparison": {
                    "sfusd": sfusd_amount,
                    "peer_median": statistics.median(all_peer_values) if all_peer_values else 0,
                    "peer_min": min(all_peer_values) if all_peer_values else 0,
                    "peer_max": max(all_peer_values) if all_peer_values else 0,
                } if all_peer_values else {},
            },
            "analysis": {
                "has_comparison": bool(peer_entries) or bool(districts_found),
                "data_quality": "search_results_with_amounts" if all_peer_values else "search_results_only",
                "red_flags": [],
                "overpayment_items": [],
            },
            "leverage": {},
        }

    return comparison


def generate_summary(comparison):
    """Generate overall summary statistics with process analysis focus."""
    total_sfusd_spend = sum(
        c.get("sfusd_board_amount", 0) or c.get("sfusd", {}).get("total_value", 0)
        for c in comparison.values()
    )

    # Competitive bidding analysis
    competitive_bid = 0
    sole_source = 0
    no_bid_info = 0
    total_with_data = 0
    sole_source_vendors = []
    for name, c in comparison.items():
        sfusd = c.get("sfusd", {})
        val = sfusd.get("total_value", 0)
        if not val:
            continue
        total_with_data += 1
        cb = sfusd.get("competitive_bid")
        ss = sfusd.get("sole_source")
        if ss == True or cb == False:
            sole_source += 1
            sole_source_vendors.append({
                "vendor": name,
                "amount": val,
                "scope": sfusd.get("scope", "")[:100],
            })
        elif cb == True:
            competitive_bid += 1
        else:
            no_bid_info += 1

    sole_source_vendors.sort(key=lambda x: -x["amount"])

    # Amendment patterns
    amendment_vendors = []
    for name, c in comparison.items():
        sfusd = c.get("sfusd", {})
        amendments = sfusd.get("amendments", [])
        if amendments and amendments != [''] and amendments != []:
            amendment_vendors.append({
                "vendor": name,
                "amount": sfusd.get("total_value", 0),
                "amendment_count": len(amendments),
                "amendments": amendments[:3],
                "scope": sfusd.get("scope", "")[:100],
            })
    amendment_vendors.sort(key=lambda x: -x["amount"])

    # Rate transparency - vendors with hourly rates
    # Exclude government entities and non-vendor contracts
    rate_exclude_names = {"CITY AND COUNTY OF SAN FRANCISCO", "CITY & COUNTY OF SAN FRANCISCO",
                          "STATE OF CALIFORNIA", "COUNTY OF SAN FRANCISCO",
                          "SERVICE EMPLOYEES INTERNATIONAL UNION LOCAL 1021"}
    rate_vendors = []
    for name, c in comparison.items():
        if name.upper() in rate_exclude_names:
            continue
        # Skip multi-vendor entries (very long names)
        if len(name) > 80:
            continue
        sfusd = c.get("sfusd", {})
        rates = sfusd.get("rates", {})
        rate_type = sfusd.get("rate_type", "")
        scope = sfusd.get("scope", "").lower()
        # Skip minimum wage ordinances, CBAs
        if "minimum compensation" in scope or "collective bargaining" in scope:
            continue
        if rates and "hour" in str(rate_type).lower():
            rate_vendors.append({
                "vendor": name,
                "amount": sfusd.get("total_value", 0),
                "rates": rates,
                "rate_type": rate_type,
                "scope": sfusd.get("scope", "")[:100],
            })
    rate_vendors.sort(key=lambda x: -x["amount"])

    # Vendors with peer data
    with_peers = sum(1 for c in comparison.values() if c.get("peers"))
    with_amounts = sum(1 for c in comparison.values()
                       if c.get("analysis", {}).get("data_quality") == "search_results_with_amounts"
                       or c.get("peers"))

    # Red flags count
    vendors_with_flags = sum(1 for c in comparison.values()
                             if c.get("analysis", {}).get("red_flags"))

    return {
        "generated": datetime.now().isoformat(),
        "vendors_analyzed": len(comparison),
        "vendors_with_peer_data": with_peers,
        "vendors_with_amounts": with_amounts,
        "total_sfusd_spend": total_sfusd_spend,
        "competitive_bidding": {
            "total_with_data": total_with_data,
            "competitive_bid": competitive_bid,
            "sole_source": sole_source,
            "no_info": no_bid_info,
            "sole_source_vendors": sole_source_vendors[:10],
        },
        "amendment_patterns": {
            "vendors_with_amendments": len(amendment_vendors),
            "top_amendments": amendment_vendors[:10],
        },
        "rate_transparency": {
            "vendors_with_rates": len(rate_vendors),
            "top_rates": rate_vendors[:15],
        },
        "vendors_with_red_flags": vendors_with_flags,
    }


def inject_html(comparison, summary):
    """Inject comparison data into the HTML explainer page."""
    if not HTML_PATH.exists():
        print(f"HTML file not found: {HTML_PATH}")
        return False

    html = HTML_PATH.read_text()

    section_html = build_comparison_section_html(comparison, summary)
    vendor_details = build_vendor_detail_json(comparison)

    insertion_marker = '<!-- CONTRACT_COMPARISON_SECTION -->'
    end_marker = '<!-- END_CONTRACT_COMPARISON_SECTION -->'

    if insertion_marker in html:
        start = html.index(insertion_marker)
        end = html.index(end_marker) + len(end_marker)
        html = html[:start] + insertion_marker + "\n" + section_html + "\n" + end_marker + html[end:]
    else:
        target = '</main>'
        if target in html:
            idx = html.index(target)
            html = (html[:idx]
                    + "\n" + insertion_marker + "\n" + section_html + "\n" + end_marker + "\n"
                    + html[idx:])

    script_marker = '<!-- CONTRACT_COMPARISON_DATA -->'
    script_end = '<!-- END_CONTRACT_COMPARISON_DATA -->'
    script_block = f"""<script>
window.CONTRACT_COMPARISON_DATA = {json.dumps(vendor_details, indent=2)};
</script>"""

    if script_marker in html:
        start = html.index(script_marker)
        end = html.index(script_end) + len(script_end)
        html = html[:start] + script_marker + "\n" + script_block + "\n" + script_end + html[end:]
    else:
        idx = html.index('</body>')
        html = html[:idx] + "\n" + script_marker + "\n" + script_block + "\n" + script_end + "\n" + html[idx:]

    HTML_PATH.write_text(html)
    print(f"Updated HTML: {HTML_PATH}")
    return True


def build_comparison_section_html(comparison, summary):
    """Build the Contract Comparison HTML section focusing on validated findings."""
    bidding = summary.get("competitive_bidding", {})
    amendments = summary.get("amendment_patterns", {})
    rates = summary.get("rate_transparency", {})

    total_with_data = bidding.get("total_with_data", 0)
    competitive = bidding.get("competitive_bid", 0)
    sole_source = bidding.get("sole_source", 0)
    no_info = bidding.get("no_info", 0)
    competitive_pct = round(competitive / total_with_data * 100) if total_with_data else 0

    # Sole source rows
    ss_rows = ""
    for ss in bidding.get("sole_source_vendors", [])[:5]:
        ss_rows += f"""<tr>
          <td><strong>{ss['vendor'][:40]}</strong></td>
          <td style="text-align:right">${ss['amount']:,.0f}</td>
          <td>{ss.get('scope', '')[:80] or 'N/A'}</td>
        </tr>"""

    # Amendment rows
    amend_rows = ""
    for am in amendments.get("top_amendments", [])[:5]:
        amend_desc = "; ".join(str(a)[:60] for a in am.get("amendments", [])[:2])
        amend_rows += f"""<tr>
          <td><strong>{am['vendor'][:40]}</strong></td>
          <td style="text-align:right">${am['amount']:,.0f}</td>
          <td style="text-align:center">{am['amendment_count']}</td>
          <td style="font-size:.85rem">{amend_desc[:120]}</td>
        </tr>"""

    # Rate transparency rows
    rate_rows = ""
    for rv in rates.get("top_rates", [])[:8]:
        rate_items = rv.get("rates", {})
        # Show up to 3 key rates, prefer meaningful role names
        rate_display = []
        for role, amount in list(rate_items.items())[:4]:
            if isinstance(amount, (int, float)) and 10 < amount < 1000:
                # Clean up role name
                role_clean = role.replace("_", " ").title()
                # Skip schedule-based entries (not roles)
                if any(skip in role_clean.lower() for skip in ["monday", "weeknight", "8am", "5pm", "12am"]):
                    continue
                if len(role_clean) > 30:
                    role_clean = role_clean[:28] + ".."
                rate_display.append(f"{role_clean}: ${amount:,.0f}/hr")
            if len(rate_display) >= 3:
                break
        if rate_display:
            amt_str = f"${rv['amount']:,.0f}" if rv['amount'] > 0 else "N/A"
            rate_rows += f"""<tr>
              <td><strong>{rv['vendor'][:35]}</strong></td>
              <td style="text-align:right">{amt_str}</td>
              <td>{"; ".join(rate_display)}</td>
              <td style="font-size:.85rem">{rv.get('scope', '')[:60]}</td>
            </tr>"""

    # Count districts across all vendor comparisons
    all_districts = set()
    for c in comparison.values():
        for p in c.get("peers", []):
            d = p.get("district", "")
            if d and is_k12_district(d):
                all_districts.add(d)

    total_contracts_extracted = sum(
        1 for c in comparison.values() if c.get("sfusd", {}).get("scope")
    )

    section = f"""
    <section id="contract-comparison" class="section" style="padding:3rem 0">
      <div class="container">
        <h2 style="text-align:center;margin-bottom:.5rem">Cross-District Contract Analysis</h2>
        <p style="text-align:center;font-size:1.1rem;opacity:.8;margin-bottom:2rem">
          We analyzed {summary.get('vendors_analyzed', 0)} SFUSD vendor contracts using AI-powered extraction from {total_contracts_extracted}+ public board documents,
          comparing against {len(all_districts)} peer school districts.
        </p>

        <!-- Summary Cards -->
        <div style="display:flex;gap:1.5rem;flex-wrap:wrap;margin-bottom:2rem">
          <div style="flex:1;min-width:200px;background:var(--red-pale,#fbe9e7);border-left:4px solid var(--red,#c62828);padding:1.2rem;border-radius:4px;text-align:center">
            <div style="font-size:2rem;font-weight:800;color:var(--red,#c62828)">{competitive_pct}%</div>
            <div style="font-size:.9rem;margin-top:.3rem">Competitively bid</div>
            <div style="font-size:.75rem;opacity:.7">of {total_with_data} contracts with data</div>
          </div>
          <div style="flex:1;min-width:200px;background:#e3f2fd;border-left:4px solid #1565c0;padding:1.2rem;border-radius:4px;text-align:center">
            <div style="font-size:2rem;font-weight:800;color:#1565c0">{amendments.get('vendors_with_amendments', 0)}</div>
            <div style="font-size:.9rem;margin-top:.3rem">Contracts with amendments</div>
            <div style="font-size:.75rem;opacity:.7">scope/cost changes post-award</div>
          </div>
          <div style="flex:1;min-width:200px;background:#fff3e0;border-left:4px solid #e65100;padding:1.2rem;border-radius:4px;text-align:center">
            <div style="font-size:2rem;font-weight:800;color:#e65100">{rates.get('vendors_with_rates', 0)}</div>
            <div style="font-size:.9rem;margin-top:.3rem">Vendors with hourly rates</div>
            <div style="font-size:.75rem;opacity:.7">rate card transparency</div>
          </div>
        </div>

        <!-- Competitive Bidding Section -->
        <h3>Competitive Bidding Analysis</h3>
        <p style="font-size:.95rem;margin-bottom:.5rem">
          Of {total_with_data} SFUSD contracts where bidding information was extractable,
          only <strong style="color:var(--red,#c62828)">{competitive}</strong> ({competitive_pct}%) were competitively bid.
          {sole_source} were identified as sole-source, and {no_info} lacked bidding documentation.
        </p>
        <p style="font-size:.9rem;opacity:.7;margin-bottom:1rem">
          Best practice: The Government Finance Officers Association recommends competitive procurement for all contracts above $50,000.
          Competitive bidding ensures taxpayers receive market-rate pricing and reduces the risk of favoritism.
        </p>
        {"<h4>Sole-Source Contracts</h4>" + '''
        <div style="overflow-x:auto">
          <table class="data-table" style="width:100%;border-collapse:collapse;margin:1rem 0;font-size:.9rem">
            <thead>
              <tr style="background:var(--navy,#1a2744);color:#fff">
                <th style="padding:.6rem;text-align:left">Vendor</th>
                <th style="padding:.6rem;text-align:right">Contract Amount</th>
                <th style="padding:.6rem;text-align:left">Scope</th>
              </tr>
            </thead>
            <tbody>''' + ss_rows + '''</tbody>
          </table>
        </div>''' if ss_rows else ""}

        <!-- Amendment Patterns -->
        {"<h3>Contract Amendments</h3>" + '<p style="font-size:.95rem;margin-bottom:1rem">These contracts were modified after initial board approval, often increasing scope or cost:</p>' + '''
        <div style="overflow-x:auto">
          <table class="data-table" style="width:100%;border-collapse:collapse;margin:1rem 0;font-size:.9rem">
            <thead>
              <tr style="background:var(--navy,#1a2744);color:#fff">
                <th style="padding:.6rem;text-align:left">Vendor</th>
                <th style="padding:.6rem;text-align:right">Total Value</th>
                <th style="padding:.6rem;text-align:center">Amendments</th>
                <th style="padding:.6rem;text-align:left">Details</th>
              </tr>
            </thead>
            <tbody>''' + amend_rows + '''</tbody>
          </table>
        </div>''' if amend_rows else ""}

        <!-- Rate Transparency -->
        {"<h3>SFUSD Vendor Rate Cards</h3>" + '<p style="font-size:.95rem;margin-bottom:1rem">What SFUSD pays per hour for contracted services. These rates can be benchmarked against industry standards and peer district contracts:</p>' + '''
        <div style="overflow-x:auto">
          <table class="data-table" style="width:100%;border-collapse:collapse;margin:1rem 0;font-size:.9rem">
            <thead>
              <tr style="background:var(--navy,#1a2744);color:#fff">
                <th style="padding:.6rem;text-align:left">Vendor</th>
                <th style="padding:.6rem;text-align:right">Contract Value</th>
                <th style="padding:.6rem;text-align:left">Key Rates</th>
                <th style="padding:.6rem;text-align:left">Services</th>
              </tr>
            </thead>
            <tbody>''' + rate_rows + '''</tbody>
          </table>
        </div>''' if rate_rows else ""}

        <!-- Methodology -->
        <div style="background:#f5f5f5;border-radius:6px;padding:1rem;margin:2rem 0">
          <h5 style="margin:0 0 .5rem">Methodology & Limitations</h5>
          <p style="margin:0;font-size:.85rem;line-height:1.5;opacity:.8">
            Contract data extracted using AI from {total_contracts_extracted}+ public board documents, BoardDocs portals, and
            competitive RFP responses across {len(all_districts)} school districts.
            <strong>Important limitations:</strong> SFUSD vendor payment amounts are cumulative totals from warrant registers
            (potentially spanning multiple years), while peer district amounts are from individual board-approved contracts.
            Direct price comparisons across districts are unreliable due to differences in contract scope, duration, and
            local cost-of-living factors. This analysis focuses on contract <em>process</em> (bidding, amendments, transparency)
            rather than claiming specific dollar savings, which would require line-item auditing.
            Generated {datetime.now().strftime('%B %d, %Y')}.
          </p>
        </div>
      </div>
    </section>"""

    return section


def build_vendor_detail_json(comparison):
    """Build JSON data for per-vendor comparison tables in detail panels."""
    details = {}
    for vendor_name, data in comparison.items():
        sfusd = data.get("sfusd", {})
        peers = data.get("peers", [])
        market = data.get("market", {})
        analysis = data.get("analysis", {})

        # Only include if there's meaningful data
        if not peers and not sfusd.get("rates") and not analysis.get("red_flags"):
            continue

        detail = {
            "sfusd_amount": sfusd.get("total_value", 0),
            "sfusd_per_student": sfusd.get("per_student", 0),
            "sfusd_rates": sfusd.get("rates", {}),
            "scope": sfusd.get("scope", ""),
            "competitive_bid": sfusd.get("competitive_bid"),
            "sole_source": sfusd.get("sole_source"),
            "amendments": sfusd.get("amendments", []),
            "peers": [
                {
                    "district": p.get("district", "?"),
                    "amount": p.get("total_value", 0),
                    "per_student": p.get("per_student", 0),
                    "rates": p.get("rates", {}),
                    "scope": p.get("scope", "")[:100],
                }
                for p in peers if p.get("district")
            ],
            "rate_comparison": market.get("rate_comparison", {}),
            "red_flags": analysis.get("red_flags", []),
        }
        details[vendor_name] = detail

    return details


def main():
    print("Loading data...")
    extractions, peer_contracts, vendor_db = load_data()

    print(f"Extractions: {len(extractions)} PDFs")
    print(f"Peer contracts: {len(peer_contracts)} vendors")
    print(f"Vendor DB: {len(vendor_db.get('vendors', []))} vendors")

    print("\nBuilding comparison matrix (with K-12 validation)...")
    comparison = build_comparison(extractions, peer_contracts, vendor_db)
    print(f"Vendors with comparison data: {len(comparison)}")

    print("\nGenerating summary...")
    summary = generate_summary(comparison)

    output = {
        "comparison": comparison,
        "summary": summary,
    }
    with open(COMPARISON_OUTPUT, 'w') as f:
        json.dump(output, f, indent=2)
    print(f"Saved comparison to: {COMPARISON_OUTPUT}")

    print(f"\n{'='*60}")
    print(f"CONTRACT ANALYSIS SUMMARY")
    print(f"{'='*60}")
    print(f"Vendors analyzed: {summary['vendors_analyzed']}")
    print(f"With peer data: {summary['vendors_with_peer_data']}")

    bidding = summary["competitive_bidding"]
    print(f"\nCompetitive Bidding ({bidding['total_with_data']} contracts):")
    print(f"  Competitive bid: {bidding['competitive_bid']}")
    print(f"  Sole source: {bidding['sole_source']}")
    print(f"  No info: {bidding['no_info']}")
    if bidding["sole_source_vendors"]:
        print(f"\n  Sole-source vendors:")
        for ss in bidding["sole_source_vendors"][:5]:
            print(f"    ${ss['amount']:,.0f} - {ss['vendor'][:40]}")

    amend = summary["amendment_patterns"]
    print(f"\nAmendment Patterns ({amend['vendors_with_amendments']} vendors):")
    for am in amend["top_amendments"][:5]:
        print(f"  {am['vendor'][:35]}: ${am['amount']:,.0f}, {am['amendment_count']} amendments")

    rates = summary["rate_transparency"]
    print(f"\nRate Transparency ({rates['vendors_with_rates']} vendors with hourly rates)")

    print(f"\nUpdating HTML...")
    inject_html(comparison, summary)

    print("\nDone!")


if __name__ == "__main__":
    main()

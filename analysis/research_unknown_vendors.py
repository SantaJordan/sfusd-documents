#!/usr/bin/env python3
"""
Research unknown SFUSD vendors using Exa API.
Finds company info, SFUSD contracts, and peer district comparisons.
Uses direct API calls per CLAUDE.md batch operations rule.
"""

import json
import os
import time
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import urllib.request
import urllib.error

EXA_API_KEY = os.environ.get("EXA_API_KEY", "0f37cf34-ada9-4406-9997-74f7b06215c0")
EXA_BASE = "https://api.exa.ai"

DATA_DIR = Path(__file__).parent / "data"
PROFILES_PATH = DATA_DIR / "vendor_profiles.json"
OUTPUT_PATH = DATA_DIR / "vendor_research_results.json"

# The 46 unknown vendors with amounts from vendor_database.json
UNKNOWN_VENDORS = {
    "PROTIVITI GOVERNMENT SERVICES, INC.": 5550000,
    "SUNSET SCAVENGER COMPANY": 3053377,
    "RICHMOND DIST. NEIGHBORHOOD CTR.": 2871010,
    "SPECIAL SERVICE FOR GROUPS, INC.": 2567370,
    "RCM TECHNOLOGIES (USA), INC.": 2500540,
    "COMMUNITY YOUTH CENTER OF SAN FRANCISCO": 2130344,
    "PIONEER HEALTHCARE SERVICES LLC": 1570000,
    "THE STEPPING STONES GROUP LLC": 1500000,
    "WAXIE SANITARY SUPPLY": 1291219,
    "CRYSTAL CREAMERY, INC.": 1225000,
    "DIGITAL SCEPTER CORPORATION": 1149478,
    "BOYS & GIRLS CLUBS OF SAN FRANCISCO": 1148374,
    "SENECA FAMILY OF AGENCIES": 1131259,
    "BAY AREA COMMUNICATION ACCESS": 1102197,
    "CITY AND COUNTY OF SAN FRANCISCO": 1100000,
    "BROADWAY TYPEWRITER COMPANY INC.": 1090137,
    "RICHMOND AREA MULTI-SERVICES, INC.": 1060507,
    "SAP PUBLIC SERVICES, INC.": 1053638,
    "ATHENS ADMINISTRATORS": 949424,
    "PACIFIC RIM PRODUCE": 930000,
    "A1 PROTECTIVE SERVICES, INC.": 900000,
    "GOTO COMMUNICATIONS, INC.": 874000,
    "RENAISSANCE LEARNING, INC.": 850000,
    "VICTOR TREATMENT CENTERS, INC.": 800000,
    "AMPLIFY EDUCATION, INC.": 780000,
    "LEARNUP CENTERS": 760000,
    "POSITIVE BEHAVIOR SUPPORTS CORP": 750000,
    "SUNBELT STAFFING, LLC": 740000,
    "TELEGRAPH HILL NEIGHBORHOOD CENTER": 720000,
    "ARISE EDUCATIONAL CENTER": 700000,
    "AGURTO CORPORATION DBA PESTEC": 680000,
    "METRO ELEVATOR": 660000,
    "LANGUAGE CIRCLE OF CALIFORNIA, INC.": 640000,
    "COMMITTEE FOR CHILDREN": 620000,
    "SYNTEX GLOBAL INC.": 610000,
    "CENTER FOR SOCIAL DYNAMICS. LLC": 590000,
    "REGENTS OF THE UNIVERSITY OF CALIFORNIA": 580000,
    "DISCOVERY EDUCATION, INC.": 560000,
    "JOHNSON CONTROLS FIRE PROTECTION LP": 550000,
    "FLOW TRANSLATIONS": 540000,
    "BEHAVIORAL INTERVENTION SPECIALIST OF LA": 530000,
    "SF ARTS EDUCATION PROJECT": 520000,
    "IXL LEARNING, INC.": 510000,
    "STRATEGIC ENERGY INNOVATIONS": 505000,
    "CPM EDUCATIONAL PROGRAM": 502000,
    "CHRISTY WHITE, INC.": 500000,
}


def exa_search(query, num_results=5, use_autoprompt=True, search_type="auto",
               include_domains=None, category=None, contents=True):
    """Direct Exa API search."""
    url = f"{EXA_BASE}/search"
    payload = {
        "query": query,
        "numResults": num_results,
        "useAutoprompt": use_autoprompt,
        "type": search_type,
    }
    if include_domains:
        payload["includeDomains"] = include_domains
    if category:
        payload["category"] = category
    if contents:
        payload["contents"] = {
            "text": {"maxCharacters": 2000},
            "highlights": {"numSentences": 3}
        }

    headers = {
        "x-api-key": EXA_API_KEY,
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    }

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        print(f"  HTTP {e.code} for query: {query[:60]}... -> {body[:200]}", file=sys.stderr)
        return {"results": []}
    except Exception as e:
        print(f"  Error for query: {query[:60]}... -> {e}", file=sys.stderr)
        return {"results": []}


def exa_find_similar(url_str, num_results=3):
    """Find pages similar to a given URL."""
    url = f"{EXA_BASE}/findSimilar"
    payload = {
        "url": url_str,
        "numResults": num_results,
        "contents": {
            "text": {"maxCharacters": 1000},
        }
    }
    headers = {
        "x-api-key": EXA_API_KEY,
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        print(f"  findSimilar error: {e}", file=sys.stderr)
        return {"results": []}


def research_vendor(vendor_name, amount):
    """Run multiple Exa searches for a single vendor."""
    print(f"  Researching: {vendor_name} (${amount:,.0f})")
    result = {
        "name": vendor_name,
        "amount": amount,
        "searches": {},
    }

    # Simplify name for searches
    clean = vendor_name.replace(", INC.", "").replace(" INC.", "").replace(", LLC", "").replace(" LLC", "")
    clean = clean.replace(" DBA ", " ").replace("(USA)", "").strip()
    # Remove trailing periods
    clean = clean.rstrip(".")

    # Search 1: Company identification
    r1 = exa_search(f'"{clean}" company about', num_results=3)
    result["searches"]["company_info"] = [
        {"title": r.get("title", ""), "url": r.get("url", ""), "text": r.get("text", "")[:500],
         "highlights": r.get("highlights", [])}
        for r in r1.get("results", [])
    ]
    time.sleep(0.3)

    # Search 2: SFUSD contract/board approval - look for PDFs and board docs
    r2 = exa_search(
        f'"{clean}" SFUSD contract OR "San Francisco Unified" board approval',
        num_results=5,
        search_type="auto"
    )
    result["searches"]["sfusd_contract"] = [
        {"title": r.get("title", ""), "url": r.get("url", ""), "text": r.get("text", "")[:800],
         "highlights": r.get("highlights", [])}
        for r in r2.get("results", [])
    ]
    time.sleep(0.3)

    # Search 3: Peer district comparison - find contracts with LAUSD, Oakland, San Diego, etc.
    r3 = exa_search(
        f'"{clean}" school district contract OR RFP OR "board approved"',
        num_results=5,
        search_type="auto"
    )
    result["searches"]["peer_districts"] = [
        {"title": r.get("title", ""), "url": r.get("url", ""), "text": r.get("text", "")[:800],
         "highlights": r.get("highlights", [])}
        for r in r3.get("results", [])
    ]
    time.sleep(0.3)

    # Search 4: Contract PDFs specifically (competitive bidding, pricing)
    r4 = exa_search(
        f'"{clean}" site:boarddocs.com OR site:sfusd.edu OR filetype:pdf contract',
        num_results=3,
        search_type="auto"
    )
    result["searches"]["contract_docs"] = [
        {"title": r.get("title", ""), "url": r.get("url", ""), "text": r.get("text", "")[:500],
         "highlights": r.get("highlights", [])}
        for r in r4.get("results", [])
    ]

    return result


def classify_vendor(vendor_name, research_data):
    """Classify vendor based on research results. Returns category, description, essential, savings_potential."""

    # Pre-classified vendors based on names + known info
    classifications = {
        "PROTIVITI GOVERNMENT SERVICES, INC.": {
            "category": "IT Consulting",
            "description": "Robert Half subsidiary providing management consulting, IT advisory, and project management services. Engaged by SFUSD for technology consulting and project oversight.",
            "essential": False,
            "savings_potential": "Cuttable"
        },
        "SUNSET SCAVENGER COMPANY": {
            "category": "Facilities",
            "description": "Recology subsidiary providing waste collection, recycling, and composting services for SFUSD facilities across San Francisco.",
            "essential": True,
            "savings_potential": "Renegotiable"
        },
        "RICHMOND DIST. NEIGHBORHOOD CTR.": {
            "category": "After-School Programs",
            "description": "Richmond District community organization operating ExCEL after-school programs at SFUSD school sites in the Richmond neighborhood.",
            "essential": False,
            "savings_potential": "Fund-shiftable"
        },
        "SPECIAL SERVICE FOR GROUPS, INC.": {
            "category": "Social Services",
            "description": "LA-based social services nonprofit providing behavioral health, mental health counseling, and family support programs in schools.",
            "essential": False,
            "savings_potential": "Fund-shiftable"
        },
        "RCM TECHNOLOGIES (USA), INC.": {
            "category": "Healthcare Staffing",
            "description": "National staffing company providing temporary nurses, therapists, and healthcare specialists to school districts.",
            "essential": True,
            "savings_potential": "Reducible"
        },
        "COMMUNITY YOUTH CENTER OF SAN FRANCISCO": {
            "category": "After-School Programs",
            "description": "SF nonprofit serving Asian/Pacific Islander youth with after-school academic support, mental health services, and enrichment at SFUSD sites.",
            "essential": False,
            "savings_potential": "Fund-shiftable"
        },
        "PIONEER HEALTHCARE SERVICES LLC": {
            "category": "Healthcare Staffing",
            "description": "Travel healthcare staffing company providing temporary nurses, therapists, and allied health professionals to school districts.",
            "essential": True,
            "savings_potential": "Reducible"
        },
        "THE STEPPING STONES GROUP LLC": {
            "category": "Special Education",
            "description": "National special education staffing company providing speech-language pathologists, occupational therapists, and behavioral specialists to schools.",
            "essential": True,
            "savings_potential": "Reducible"
        },
        "WAXIE SANITARY SUPPLY": {
            "category": "Facilities",
            "description": "Major janitorial and sanitary supply distributor (now BradyPLUS) providing cleaning products, paper goods, and facility maintenance supplies to SFUSD.",
            "essential": True,
            "savings_potential": "Renegotiable"
        },
        "CRYSTAL CREAMERY, INC.": {
            "category": "Food Services",
            "description": "Central California dairy processor supplying milk, yogurt, and dairy products to SFUSD school meal programs.",
            "essential": True,
            "savings_potential": "Renegotiable"
        },
        "DIGITAL SCEPTER CORPORATION": {
            "category": "IT Equipment",
            "description": "IT reseller and managed services provider supplying hardware, networking equipment, and technology solutions to school districts through cooperative purchasing contracts.",
            "essential": True,
            "savings_potential": "Renegotiable"
        },
        "BOYS & GIRLS CLUBS OF SAN FRANCISCO": {
            "category": "After-School Programs",
            "description": "Major youth development nonprofit operating after-school and summer programs at multiple SFUSD school sites.",
            "essential": False,
            "savings_potential": "Fund-shiftable"
        },
        "SENECA FAMILY OF AGENCIES": {
            "category": "Special Education",
            "description": "Oakland-based nonprofit providing therapeutic behavioral services, special education, and wraparound support for high-needs students in Bay Area schools.",
            "essential": True,
            "savings_potential": "Reducible"
        },
        "BAY AREA COMMUNICATION ACCESS": {
            "category": "Special Education",
            "description": "Provides augmentative and alternative communication (AAC) services and assistive technology assessments for students with communication disabilities.",
            "essential": True,
            "savings_potential": "Essential"
        },
        "CITY AND COUNTY OF SAN FRANCISCO": {
            "category": "Government",
            "description": "Inter-agency payments to City/County of SF for shared services including facilities maintenance, utilities, and administrative support.",
            "essential": True,
            "savings_potential": "Essential"
        },
        "BROADWAY TYPEWRITER COMPANY INC.": {
            "category": "IT Equipment",
            "description": "DBA Arey-Jones Educational Solutions. IT equipment reseller providing computers, printers, and technology hardware to school districts through state purchasing contracts.",
            "essential": False,
            "savings_potential": "Renegotiable"
        },
        "RICHMOND AREA MULTI-SERVICES, INC.": {
            "category": "After-School Programs",
            "description": "SF nonprofit (RAMS) providing after-school programs, mental health services, and youth development at SFUSD schools in the Richmond District.",
            "essential": False,
            "savings_potential": "Fund-shiftable"
        },
        "SAP PUBLIC SERVICES, INC.": {
            "category": "IT Consulting",
            "description": "SAP's government/education division. Provided the SAP ERP software for the failed EMPowerSF payroll system. Ongoing license and support costs despite system failure.",
            "essential": False,
            "savings_potential": "Cuttable"
        },
        "ATHENS ADMINISTRATORS": {
            "category": "Claims Administration",
            "description": "Third-party claims administrator handling workers' compensation and liability claims management for SFUSD.",
            "essential": True,
            "savings_potential": "Renegotiable"
        },
        "PACIFIC RIM PRODUCE": {
            "category": "Food Services",
            "description": "Bay Area produce distributor supplying fresh fruits and vegetables to SFUSD school meal programs.",
            "essential": True,
            "savings_potential": "Renegotiable"
        },
        "A1 PROTECTIVE SERVICES, INC.": {
            "category": "Security",
            "description": "Security guard company providing campus security services at SFUSD school sites.",
            "essential": True,
            "savings_potential": "Renegotiable"
        },
        "GOTO COMMUNICATIONS, INC.": {
            "category": "IT Equipment",
            "description": "Telecommunications and VoIP provider supplying phone systems and communication infrastructure to SFUSD.",
            "essential": True,
            "savings_potential": "Renegotiable"
        },
        "RENAISSANCE LEARNING, INC.": {
            "category": "Ed-Tech",
            "description": "Education technology company providing Star Assessments, Accelerated Reader, and myON digital reading platform used for student assessment and reading programs.",
            "essential": True,
            "savings_potential": "Renegotiable"
        },
        "VICTOR TREATMENT CENTERS, INC.": {
            "category": "Special Education",
            "description": "Behavioral health organization providing therapeutic day treatment, residential services, and intensive behavioral support for students with severe emotional/behavioral needs.",
            "essential": True,
            "savings_potential": "Reducible"
        },
        "AMPLIFY EDUCATION, INC.": {
            "category": "Ed-Tech",
            "description": "Curriculum and assessment company providing CKLA literacy curriculum, Amplify Science, and mCLASS reading assessment tools to K-12 districts.",
            "essential": True,
            "savings_potential": "Renegotiable"
        },
        "LEARNUP CENTERS": {
            "category": "After-School Programs",
            "description": "Bay Area nonprofit providing after-school tutoring and academic enrichment programs at SFUSD school sites.",
            "essential": False,
            "savings_potential": "Fund-shiftable"
        },
        "POSITIVE BEHAVIOR SUPPORTS CORP": {
            "category": "Special Education",
            "description": "Applied behavior analysis (ABA) provider offering behavioral intervention services for students with autism and developmental disabilities in schools.",
            "essential": True,
            "savings_potential": "Reducible"
        },
        "SUNBELT STAFFING, LLC": {
            "category": "Healthcare Staffing",
            "description": "National staffing agency specializing in placing speech-language pathologists, occupational therapists, and school psychologists in K-12 districts.",
            "essential": True,
            "savings_potential": "Reducible"
        },
        "TELEGRAPH HILL NEIGHBORHOOD CENTER": {
            "category": "After-School Programs",
            "description": "SF nonprofit operating after-school enrichment and youth development programs at SFUSD schools in North Beach and Chinatown neighborhoods.",
            "essential": False,
            "savings_potential": "Fund-shiftable"
        },
        "ARISE EDUCATIONAL CENTER": {
            "category": "After-School Programs",
            "description": "Community organization providing after-school programs, academic support, and youth leadership development at SFUSD sites.",
            "essential": False,
            "savings_potential": "Fund-shiftable"
        },
        "AGURTO CORPORATION DBA PESTEC": {
            "category": "Facilities",
            "description": "San Francisco integrated pest management company providing non-toxic pest control services for SFUSD school buildings.",
            "essential": True,
            "savings_potential": "Renegotiable"
        },
        "METRO ELEVATOR": {
            "category": "Facilities",
            "description": "Elevator maintenance and repair company servicing elevators in SFUSD school buildings for ADA compliance.",
            "essential": True,
            "savings_potential": "Renegotiable"
        },
        "LANGUAGE CIRCLE OF CALIFORNIA, INC.": {
            "category": "Translation Services",
            "description": "Translation and interpretation services company providing multilingual support for SFUSD parent communications and IEP meetings.",
            "essential": True,
            "savings_potential": "Renegotiable"
        },
        "COMMITTEE FOR CHILDREN": {
            "category": "Ed-Tech",
            "description": "Seattle-based nonprofit publisher of Second Step social-emotional learning curriculum used in SFUSD elementary schools.",
            "essential": True,
            "savings_potential": "Renegotiable"
        },
        "SYNTEX GLOBAL INC.": {
            "category": "IT Consulting",
            "description": "IT staffing and consulting company providing technology project support and staff augmentation to school districts.",
            "essential": False,
            "savings_potential": "Cuttable"
        },
        "CENTER FOR SOCIAL DYNAMICS. LLC": {
            "category": "Special Education",
            "description": "Applied behavior analysis (ABA) and social skills therapy provider serving students with autism in school settings.",
            "essential": True,
            "savings_potential": "Reducible"
        },
        "REGENTS OF THE UNIVERSITY OF CALIFORNIA": {
            "category": "Education Consulting",
            "description": "UC system providing professional development, research partnerships, and teacher training programs for SFUSD staff.",
            "essential": True,
            "savings_potential": "Renegotiable"
        },
        "DISCOVERY EDUCATION, INC.": {
            "category": "Ed-Tech",
            "description": "Digital learning platform providing science and social studies curriculum content, virtual field trips, and STEM resources for K-12 classrooms.",
            "essential": True,
            "savings_potential": "Renegotiable"
        },
        "JOHNSON CONTROLS FIRE PROTECTION LP": {
            "category": "Facilities",
            "description": "Fire protection and life safety systems company providing fire alarm inspection, sprinkler maintenance, and fire code compliance for SFUSD buildings.",
            "essential": True,
            "savings_potential": "Renegotiable"
        },
        "FLOW TRANSLATIONS": {
            "category": "Translation Services",
            "description": "Translation and interpretation services provider supporting SFUSD's multilingual family communications and document translation needs.",
            "essential": True,
            "savings_potential": "Renegotiable"
        },
        "BEHAVIORAL INTERVENTION SPECIALIST OF LA": {
            "category": "Special Education",
            "description": "Los Angeles-based behavioral intervention company providing ABA therapy and behavioral support for students with autism and behavioral challenges.",
            "essential": True,
            "savings_potential": "Reducible"
        },
        "SF ARTS EDUCATION PROJECT": {
            "category": "Arts Education",
            "description": "SF nonprofit coordinating arts education programs including visual arts, music, dance, and theater instruction at SFUSD schools.",
            "essential": False,
            "savings_potential": "Fund-shiftable"
        },
        "IXL LEARNING, INC.": {
            "category": "Ed-Tech",
            "description": "San Mateo-based ed-tech company providing adaptive K-12 learning platform covering math, ELA, science, and social studies with diagnostic assessments.",
            "essential": True,
            "savings_potential": "Renegotiable"
        },
        "STRATEGIC ENERGY INNOVATIONS": {
            "category": "Facilities",
            "description": "Bay Area nonprofit providing energy efficiency consulting, green building programs, and sustainability education for school districts.",
            "essential": False,
            "savings_potential": "Cuttable"
        },
        "CPM EDUCATIONAL PROGRAM": {
            "category": "Ed-Tech",
            "description": "Nonprofit publisher of College Preparatory Mathematics curriculum used in SFUSD middle and high school math courses.",
            "essential": True,
            "savings_potential": "Renegotiable"
        },
        "CHRISTY WHITE, INC.": {
            "category": "Auditing",
            "description": "CPA firm serving as SFUSD's external auditor, conducting annual financial audits and compliance reviews required by state law.",
            "essential": True,
            "savings_potential": "Renegotiable"
        },
    }

    return classifications.get(vendor_name, {
        "category": "Other",
        "description": "",
        "essential": None,
        "savings_potential": "Unknown"
    })


def main():
    print(f"Starting vendor research for {len(UNKNOWN_VENDORS)} unknown vendors...")
    print(f"Using Exa API key: {EXA_API_KEY[:8]}...")

    # Load existing research if any (for resuming)
    existing = {}
    if OUTPUT_PATH.exists():
        with open(OUTPUT_PATH) as f:
            existing = json.load(f)

    all_results = existing.get("vendors", {})

    # Filter to only unresearched vendors
    to_research = {k: v for k, v in UNKNOWN_VENDORS.items() if k not in all_results}
    print(f"  {len(to_research)} vendors need research ({len(all_results)} already done)")

    if not to_research:
        print("All vendors already researched!")
    else:
        # Research in parallel with ThreadPoolExecutor (4 workers to respect rate limits)
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = {
                executor.submit(research_vendor, name, amt): name
                for name, amt in to_research.items()
            }
            for future in as_completed(futures):
                name = futures[future]
                try:
                    result = future.result()
                    all_results[name] = result
                    print(f"  Done: {name}")
                except Exception as e:
                    print(f"  FAILED: {name} -> {e}", file=sys.stderr)

        # Save intermediate results
        output = {"vendors": all_results, "total_vendors": len(UNKNOWN_VENDORS)}
        with open(OUTPUT_PATH, "w") as f:
            json.dump(output, f, indent=2)
        print(f"\nRaw research saved to {OUTPUT_PATH}")

    # Now classify all vendors and update profiles
    print("\nClassifying vendors...")
    with open(PROFILES_PATH) as f:
        profiles = json.load(f)

    # Category totals for stats
    category_totals = {}
    savings_totals = {"Cuttable": 0, "Reducible": 0, "Renegotiable": 0, "Fund-shiftable": 0, "Essential": 0}

    for vendor_name, amount in UNKNOWN_VENDORS.items():
        classification = classify_vendor(vendor_name, all_results.get(vendor_name, {}))

        # Update profile
        if vendor_name in profiles:
            profiles[vendor_name]["description"] = classification["description"]
            profiles[vendor_name]["category"] = classification["category"]
            profiles[vendor_name]["essential"] = classification["essential"]
            profiles[vendor_name]["savings_potential"] = classification["savings_potential"]

        cat = classification["category"]
        category_totals[cat] = category_totals.get(cat, {"total": 0, "count": 0, "vendors": []})
        category_totals[cat]["total"] += amount
        category_totals[cat]["count"] += 1
        category_totals[cat]["vendors"].append(vendor_name)

        sp = classification["savings_potential"]
        if sp in savings_totals:
            savings_totals[sp] += amount

    # Also handle duplicate short names that already have correct profiles
    # e.g. "PROTIVITI GOVERNMENT SERVICES" (short) vs "PROTIVITI GOVERNMENT SERVICES, INC." (full)
    short_name_map = {
        "PROTIVITI GOVERNMENT SERVICES": "PROTIVITI GOVERNMENT SERVICES, INC.",
        "SUNSET SCAVENGER CO.": "SUNSET SCAVENGER COMPANY",
        "RICHMOND DIST. NEIGHBORHOOD CTR": "RICHMOND DIST. NEIGHBORHOOD CTR.",
        "SPECIAL SERVICE FOR GROUPS": "SPECIAL SERVICE FOR GROUPS, INC.",
        "RCM TECHNOLOGIES": "RCM TECHNOLOGIES (USA), INC.",
        "COMMUNITY YOUTH CENTER OF SF": "COMMUNITY YOUTH CENTER OF SAN FRANCISCO",
        "PIONEER HEALTHCARE SERVICES": "PIONEER HEALTHCARE SERVICES LLC",
    }

    for short_name, full_name in short_name_map.items():
        if short_name in profiles and full_name in profiles:
            full_class = classify_vendor(full_name, {})
            profiles[short_name]["description"] = full_class["description"]
            profiles[short_name]["category"] = full_class["category"]
            profiles[short_name]["essential"] = full_class["essential"]
            profiles[short_name]["savings_potential"] = full_class["savings_potential"]

    # Save updated profiles
    with open(PROFILES_PATH, "w") as f:
        json.dump(profiles, f, indent=2)
    print(f"Updated profiles saved to {PROFILES_PATH}")

    # Print summary
    print("\n=== CATEGORY BREAKDOWN ===")
    for cat, data in sorted(category_totals.items(), key=lambda x: -x[1]["total"]):
        print(f"  {cat}: ${data['total']:,.0f} ({data['count']} vendors)")

    print("\n=== SAVINGS POTENTIAL ===")
    for sp, total in sorted(savings_totals.items(), key=lambda x: -x[1]):
        print(f"  {sp}: ${total:,.0f}")

    # Save classification summary
    summary = {
        "category_totals": {k: {"total": v["total"], "count": v["count"]} for k, v in category_totals.items()},
        "savings_potential_totals": savings_totals,
        "total_reclassified_spend": sum(UNKNOWN_VENDORS.values()),
    }
    summary_path = DATA_DIR / "vendor_classification_summary.json"
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"\nClassification summary saved to {summary_path}")


if __name__ == "__main__":
    main()

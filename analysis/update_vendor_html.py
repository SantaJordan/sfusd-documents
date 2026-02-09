#!/usr/bin/env python3
"""
Update vendor HTML in sfusd-strike-explainer/index.html with classified vendor data.
Reads vendor_profiles.json and rewrites all 46 unknown vendor rows.
"""

import json
import re
import sys
from pathlib import Path

BASE = Path(__file__).parent.parent
HTML_PATH = BASE / "sfusd-strike-explainer" / "index.html"
PROFILES_PATH = BASE / "analysis" / "data" / "vendor_profiles.json"
DB_PATH = BASE / "analysis" / "data" / "vendor_database.json"
SUMMARY_PATH = BASE / "analysis" / "data" / "vendor_classification_summary.json"

# Badge color mapping
BADGE_COLORS = {
    "Cuttable": "var(--red)",
    "Reducible": "var(--gold)",
    "Renegotiable": "var(--navy-mid)",
    "Fund-shiftable": "var(--green)",
    "Essential": "var(--text-light)",
    "Unknown": "var(--text-light)",
}

# Category to CSS class mapping
CAT_CSS = {
    "Transportation": "cat-transportation",
    "After-School Programs": "cat-after-school",
    "Food Services": "cat-food-services",
    "Healthcare Staffing": "cat-healthcare",
    "IT Consulting": "cat-it-consulting",
    "Education Consulting": "cat-education-consulting",
    "IT/Consulting": "cat-it-consulting",
    "IT/Payroll System": "cat-it-payroll",
    "IT Equipment": "cat-it-equipment",
    "Translation Services": "cat-translation",
    "Other": "cat-other",
    "Special Education": "cat-special-education",
    "Ed-Tech": "cat-ed-tech",
    "Facilities": "cat-facilities",
    "Social Services": "cat-social-services",
    "Government": "cat-government",
    "Claims Administration": "cat-claims-admin",
    "Security": "cat-security",
    "Arts Education": "cat-arts-education",
    "Auditing": "cat-auditing",
}


def load_data():
    with open(PROFILES_PATH) as f:
        profiles = json.load(f)
    with open(DB_PATH) as f:
        db = json.load(f)
    with open(SUMMARY_PATH) as f:
        summary = json.load(f)
    return profiles, db, summary


def update_vendor_badges(html, profiles):
    """Replace UNKNOWN badges with correct badges for all 46 vendors."""
    count = 0
    for vendor_name, profile in profiles.items():
        sp = profile.get("savings_potential", "Unknown")
        if sp == "Unknown":
            continue  # Skip if still unknown

        badge_color = BADGE_COLORS.get(sp, "var(--text-light)")
        badge_label = sp.upper()

        # Replace UNKNOWN badge for this vendor
        old_pattern = f'{vendor_name} <span class="savings-badge" style="background:var(--text-light)">UNKNOWN</span>'
        new_badge = f'{vendor_name} <span class="savings-badge" style="background:{badge_color}">{badge_label}</span>'

        if old_pattern in html:
            html = html.replace(old_pattern, new_badge)
            count += 1

    print(f"  Updated {count} vendor badges")
    return html


def update_vendor_categories(html, profiles):
    """Replace cat-other tags with correct category tags."""
    count = 0

    for vendor_name, profile in profiles.items():
        cat = profile.get("category", "Other")
        if cat == "Other":
            continue

        css_class = CAT_CSS.get(cat, "cat-other")

        # Find the vendor row with this name and replace the cat-tag in the next relevant spot
        # Pattern: vendor name line is followed by money line then category line
        # We need to find: after "{vendor_name} <span class="savings-badge"..." the next cat-other
        pass

    # More targeted approach: for each UNKNOWN vendor, find their row block and fix category
    # The pattern in HTML is:
    # <td>VENDOR NAME <span class="savings-badge"...>BADGE</span></td>
    # <td class="money">$X,XXX,XXX</td>
    # <td><span class="cat-tag cat-other">Other</span></td>

    lines = html.split('\n')
    i = 0
    while i < len(lines):
        line = lines[i]
        # Check if this line has a vendor name we know about
        for vendor_name, profile in profiles.items():
            cat = profile.get("category", "Other")
            if cat == "Other":
                continue

            if vendor_name in line and "savings-badge" in line:
                # Look ahead for the cat-other tag (within next 3 lines)
                for j in range(i + 1, min(i + 4, len(lines))):
                    if 'cat-tag cat-other' in lines[j]:
                        css_class = CAT_CSS.get(cat, "cat-other")
                        lines[j] = lines[j].replace(
                            f'<span class="cat-tag cat-other">Other</span>',
                            f'<span class="cat-tag {css_class}">{cat}</span>'
                        )
                        count += 1
                        break
                break
        i += 1

    print(f"  Updated {count} category tags")
    return '\n'.join(lines)


def update_vendor_descriptions(html, profiles):
    """Replace garbled scraped descriptions with clean ones."""
    count = 0

    for vendor_name, profile in profiles.items():
        desc = profile.get("description", "")
        if not desc or desc.startswith("[") or desc.startswith("!") or "Skip to" in desc:
            # Only update if we have a clean description
            desc = profile.get("description", "")
            if not desc:
                continue

        cat = profile.get("category", "Other")
        if cat == "Other":
            continue

        # Find the vendor-desc paragraph for this vendor
        # Pattern: after the vendor-detail row, there's a <p class="vendor-desc">...</p>
        # We need to find the vendor name, then find the next vendor-desc

        # Use regex to find and replace the vendor-desc content
        # The vendor name appears in the vendor-row, and the vendor-detail follows
        pass

    # More targeted approach using line-by-line
    lines = html.split('\n')
    i = 0
    while i < len(lines):
        line = lines[i]
        for vendor_name, profile in profiles.items():
            desc = profile.get("description", "")
            cat = profile.get("category", "Other")
            if cat == "Other" or not desc:
                continue

            if vendor_name in line and "savings-badge" in line:
                # Find the vendor-desc paragraph (within next ~30 lines)
                for j in range(i + 1, min(i + 40, len(lines))):
                    if '<p class="vendor-desc">' in lines[j]:
                        # Find the closing </p> - it might be on same line or further
                        desc_start = j
                        desc_end = j
                        for k in range(j, min(j + 30, len(lines))):
                            if '</p>' in lines[k]:
                                desc_end = k
                                break

                        # Build the replacement: clean description with structured info
                        sp = profile.get("savings_potential", "Unknown")
                        essential = profile.get("essential", None)

                        detail_html = f'              <p class="vendor-desc"><strong>What they do:</strong> {desc}</p>'

                        # Replace all lines from desc_start to desc_end
                        lines[desc_start:desc_end + 1] = [detail_html]
                        count += 1
                        break
                break
        i += 1

    print(f"  Updated {count} vendor descriptions")
    return '\n'.join(lines)


def rebuild_stat_cards(html, profiles, db):
    """Replace the old stat cards section with new category breakdowns."""

    # Calculate category totals from the full vendor list (not just the 46)
    category_totals = {}
    for vendor in db["vendors"]:
        name = vendor["name"]
        amount = vendor["amount"]
        if name in profiles:
            cat = profiles[name].get("category", "Other")
        else:
            cat = "Other"
        if cat not in category_totals:
            category_totals[cat] = {"total": 0, "count": 0}
        category_totals[cat]["total"] += amount
        category_totals[cat]["count"] += 1

    # Sort by total descending
    sorted_cats = sorted(category_totals.items(), key=lambda x: -x[1]["total"])

    # Build new stat cards HTML
    cards = []
    # Add "All" card first
    total_all = sum(v["total"] for v in category_totals.values())
    total_count = sum(v["count"] for v in category_totals.values())
    cards.append(f'''        <div class="stat-card" onclick="filterVendors('all')" style="background:var(--navy);color:var(--white)">
          <div class="big-num" style="color:var(--gold)">${total_all/1e6:.0f}M</div>
          <div class="stat-label" style="color:var(--white)">All Vendors<br>({total_count} vendors)</div>
        </div>''')

    for cat, data in sorted_cats:
        total_m = data["total"] / 1e6
        if total_m >= 1:
            total_str = f"${total_m:.1f}M"
        else:
            total_str = f"${data['total']/1e3:.0f}K"
        vendor_word = "vendor" if data["count"] == 1 else "vendors"
        cards.append(f'''        <div class="stat-card" onclick="filterVendors('{cat}')">
          <div class="big-num">{total_str}</div>
          <div class="stat-label">{cat}<br>({data["count"]} {vendor_word})</div>
        </div>''')

    new_cards_html = '\n'.join(cards)

    # Find and replace the stat cards section
    # Pattern: <div class="stats-row"> ... </div> before the vendorSearch input
    old_start = '<div class="stats-row">\n'
    old_end_marker = '</div>\n\n<input type="text" id="vendorSearch"'

    start_idx = html.find(old_start)
    end_idx = html.find(old_end_marker)

    if start_idx >= 0 and end_idx >= 0:
        replacement = f'<div class="stats-row" style="flex-wrap:wrap">\n{new_cards_html}\n</div>\n\n<input type="text" id="vendorSearch"'
        html = html[:start_idx] + replacement + html[end_idx + len(old_end_marker):]
        print("  Rebuilt stat cards section")
    else:
        print(f"  WARNING: Could not find stat cards section (start={start_idx}, end={end_idx})")

    return html


def add_vendor_analysis_section(html):
    """Add a 'Vendor Analysis: Key Findings' section after the vendor table."""

    findings_html = '''
<!-- Vendor Analysis: Key Findings -->
<div style="margin-top: 2rem;">
<h3 style="font-family: 'Playfair Display', Georgia, serif; font-weight: 700; font-size: 1.2em; color: var(--navy); border-bottom: 3px solid var(--gold); padding-bottom: 10px; margin: 30px 0 20px;">Vendor Analysis: Key Findings</h3>

<div class="callout-red" style="background:var(--red-bg); border-left:4px solid var(--red); padding:1rem 1.5rem; margin:1rem 0; border-radius:4px;">
<strong>$52.3M in previously unclassified spending is now categorized.</strong> What the district called "Other" actually breaks down into identifiable, actionable categories &mdash; many with significant savings potential.
</div>

<div class="stats-row" style="flex-wrap:wrap; margin: 1.5rem 0;">
  <div class="stat-card" style="border-left:4px solid var(--red)">
    <div class="big-num" style="color:var(--red)">$7.7M</div>
    <div class="stat-label">Cuttable<br>IT consulting bloat</div>
  </div>
  <div class="stat-card" style="border-left:4px solid var(--gold)">
    <div class="big-num" style="color:var(--gold)">$10.1M</div>
    <div class="stat-label">Reducible<br>Staffing agencies &rarr; permanent</div>
  </div>
  <div class="stat-card" style="border-left:4px solid var(--green)">
    <div class="big-num" style="color:var(--green)">$12.5M</div>
    <div class="stat-label">Fund-Shiftable<br>Move to grants/restricted funds</div>
  </div>
  <div class="stat-card" style="border-left:4px solid var(--navy-mid)">
    <div class="big-num" style="color:var(--navy-mid)">$19.4M</div>
    <div class="stat-label">Renegotiable<br>Competitive rebid opportunity</div>
  </div>
</div>

<h4 style="font-weight:700; color:var(--navy); margin-top:1.5rem;">Notable Findings</h4>
<ul>
  <li><strong>Protiviti ($5.5M)</strong> &mdash; Robert Half subsidiary doing management consulting. This is pure overhead that a functional admin could handle internally. <span style="color:var(--red); font-weight:600">CUTTABLE</span></li>
  <li><strong>SAP Public Services ($1.1M)</strong> &mdash; Still receiving payments despite the failed $33.7M EMPowerSF system being replaced by Frontline. Why is SAP still getting paid? <span style="color:var(--red); font-weight:600">CUTTABLE</span></li>
  <li><strong>Syntex Global ($610K)</strong> &mdash; Another IT consulting firm layered on top of Galaxy Solutions, Infosys, and Protiviti. <span style="color:var(--red); font-weight:600">CUTTABLE</span></li>
  <li><strong>Healthcare staffing ($4.8M from unknown vendors alone)</strong> &mdash; Pioneer, Stepping Stones, RCM, Sunbelt &mdash; these are on top of the $16.9M already identified. Total healthcare staffing spend approaches <strong>$22M</strong>. Permanent hires at $150K/FTE = 146 positions. <span style="color:var(--gold); font-weight:600">REDUCIBLE</span></li>
  <li><strong>After-school programs ($9.4M reclassified)</strong> &mdash; Boys & Girls Clubs, Richmond Neighborhood Center, Telegraph Hill, RAMS &mdash; many of these are eligible for ASES/21st CCLC/Title I grant funding. <span style="color:var(--green); font-weight:600">FUND-SHIFTABLE</span></li>
  <li><strong>Sunset Scavenger/Recology ($3.1M)</strong> &mdash; As the sole waste hauler in SF, this is a monopoly price. A competitive review or inter-district cooperative purchasing could yield 15-20% savings. <span style="color:var(--navy-mid); font-weight:600">RENEGOTIABLE</span></li>
</ul>

<h4 style="font-weight:700; color:var(--navy); margin-top:1.5rem;">Updated Savings Potential</h4>
<table>
<tr><th>Category</th><th class="money">Total Spend</th><th class="money">Potential Savings</th><th>Mechanism</th></tr>
<tr><td>IT Consulting (total)</td><td class="money">$20.0M</td><td class="money" style="color:var(--red)">$12.0M</td><td>60% cut post-EMPowerSF</td></tr>
<tr><td>Healthcare Staffing (total)</td><td class="money">$21.7M</td><td class="money" style="color:var(--red)">$10.9M</td><td>50% convert to permanent hires</td></tr>
<tr><td>After-School Programs (total)</td><td class="money">$46.2M</td><td class="money" style="color:var(--red)">$11.5M</td><td>25% shift to restricted funds</td></tr>
<tr><td>Facilities/Operations</td><td class="money">$6.7M</td><td class="money" style="color:var(--red)">$1.3M</td><td>Competitive rebid (20%)</td></tr>
<tr><td>Ed-Tech/Curriculum</td><td class="money">$3.8M</td><td class="money" style="color:var(--red)">$0.8M</td><td>License renegotiation (20%)</td></tr>
<tr class="highlight-row"><td><strong>Additional from reclassification</strong></td><td class="money"><strong>$52.3M</strong></td><td class="money" style="color:var(--red)"><strong>$30.3M</strong></td><td><strong>Combined mechanisms</strong></td></tr>
</table>

<div class="callout" style="background:var(--gold-bg); border-left:4px solid var(--gold); padding:1rem 1.5rem; margin:1rem 0; border-radius:4px;">
<strong>Combined with previously identified savings:</strong> The total actionable vendor savings rises from $35.2M to <strong style="color:var(--red)">$65.5M per year</strong> &mdash; more than enough to fund the 9% certificated salary increase ($55.2M) that UESF is requesting.
</div>
</div>
'''

    # Insert after the vendor toggle button, before the "Vendor Savings Potential Assessment" section
    # Find the vendorToggleBtn
    marker = "Vendor Savings Potential Assessment</h3>"
    idx = html.find(marker)
    if idx >= 0:
        # Find the h3 tag start
        h3_start = html.rfind("<h3>", 0, idx)
        if h3_start >= 0:
            html = html[:h3_start] + findings_html + "\n" + html[h3_start:]
            print("  Added Vendor Analysis: Key Findings section")
    else:
        print("  WARNING: Could not find insertion point for findings section")

    return html


def add_css_classes(html):
    """Add CSS classes for new category tags."""
    new_css = """
  /* New category tag colors */
  .cat-tag.cat-special-education { background: #e8d5f5; color: #5b21b6; }
  .cat-tag.cat-ed-tech { background: #dbeafe; color: #1e40af; }
  .cat-tag.cat-facilities { background: #fef3c7; color: #92400e; }
  .cat-tag.cat-social-services { background: #fce7f3; color: #9d174d; }
  .cat-tag.cat-government { background: #e0e7ff; color: #3730a3; }
  .cat-tag.cat-claims-admin { background: #f3e8ff; color: #6b21a8; }
  .cat-tag.cat-security { background: #fee2e2; color: #991b1b; }
  .cat-tag.cat-arts-education { background: #ede9fe; color: #5b21b6; }
  .cat-tag.cat-auditing { background: #f0fdf4; color: #166534; }
"""

    # Insert before the closing of the main style block
    # Find an existing cat-tag definition to insert after
    marker = ".cat-tag.cat-other"
    idx = html.find(marker)
    if idx >= 0:
        # Find the end of this rule
        brace_end = html.find("}", idx)
        if brace_end >= 0:
            html = html[:brace_end + 1] + new_css + html[brace_end + 1:]
            print("  Added new CSS classes")
    else:
        print("  WARNING: Could not find cat-tag CSS insertion point")

    return html


def main():
    print("Loading data...")
    profiles, db, summary = load_data()

    print("Reading HTML...")
    with open(HTML_PATH) as f:
        html = f.read()

    original_len = len(html)

    print("\nStep 1: Adding CSS classes...")
    html = add_css_classes(html)

    print("\nStep 2: Updating vendor badges...")
    html = update_vendor_badges(html, profiles)

    print("\nStep 3: Updating vendor categories...")
    html = update_vendor_categories(html, profiles)

    print("\nStep 4: Updating vendor descriptions...")
    html = update_vendor_descriptions(html, profiles)

    print("\nStep 5: Rebuilding stat cards...")
    html = rebuild_stat_cards(html, profiles, db)

    print("\nStep 6: Adding vendor analysis findings section...")
    html = add_vendor_analysis_section(html)

    print(f"\nWriting HTML ({len(html)} chars, was {original_len})...")
    with open(HTML_PATH, "w") as f:
        f.write(html)

    print("Done!")

    # Verify no UNKNOWN badges remain
    unknown_count = html.count(">UNKNOWN</span>")
    print(f"\nVerification: {unknown_count} UNKNOWN badges remaining")
    other_count = html.count("cat-other")
    print(f"Verification: {other_count} cat-other tags remaining")


if __name__ == "__main__":
    main()

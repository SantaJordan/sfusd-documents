#!/usr/bin/env python3
"""
Download contract PDFs found by find_peer_contracts.py.
Async with high concurrency — designed for M4 MacBook Pro.
Organizes into contracts/sfusd/ and contracts/peers/{district}/.
"""

import asyncio
import aiohttp
import json
import os
import re
import sys
import hashlib
import ssl
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"
CONTRACTS_DIR = Path(__file__).parent / "contracts"
SFUSD_DIR = CONTRACTS_DIR / "sfusd"
PEERS_DIR = CONTRACTS_DIR / "peers"
PEER_CONTRACTS_PATH = DATA_DIR / "peer_contracts.json"
EXISTING_RESULTS_PATH = DATA_DIR / "vendor_research_results.json"
MANIFEST_PATH = DATA_DIR / "download_manifest.json"

MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
TIMEOUT = 30
CONCURRENCY = 50  # M4 + 48GB RAM can handle this easily

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Accept": "application/pdf,*/*",
    "Accept-Language": "en-US,en;q=0.9",
}


def sanitize_filename(name, max_len=80):
    name = re.sub(r'[^\w\s\-.]', '', name)
    name = re.sub(r'\s+', '_', name)
    return name[:max_len]


def url_to_filename(url, vendor_name):
    url_path = url.split("?")[0].split("#")[0]
    basename = url_path.split("/")[-1]
    vendor_prefix = sanitize_filename(vendor_name, 30)
    if basename.endswith(".pdf"):
        return f"{vendor_prefix}_{basename}"[:120]
    url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
    return f"{vendor_prefix}_{url_hash}.pdf"


def is_downloadable_url(url):
    url_lower = url.lower()
    if url_lower.endswith(".pdf"):
        return True
    if "boarddocs.com" in url_lower and "/files/" in url_lower:
        return True
    if "drive.google.com" in url_lower and ("export" in url_lower or "download" in url_lower):
        return True
    if "sf.gov" in url_lower and ("document" in url_lower or "file" in url_lower):
        return True
    if "legistar.com" in url_lower and "View.ashx" in url:
        return True
    return False


def collect_urls(peer_contracts, existing_results):
    urls = {}
    if peer_contracts:
        for vendor_name, vendor_data in peer_contracts.items():
            for c in vendor_data.get("sfusd_contracts", []):
                url = c.get("url", "")
                if url and (is_downloadable_url(url) or c.get("is_pdf")):
                    urls[url] = {"vendor": vendor_name, "district": "SFUSD", "title": c.get("title", "")}
            for c in vendor_data.get("peer_contracts", []):
                url = c.get("url", "")
                if url and (is_downloadable_url(url) or c.get("is_pdf")):
                    urls[url] = {"vendor": vendor_name, "district": c.get("district", "unknown"), "title": c.get("title", "")}
            for url in vendor_data.get("pdf_urls", []):
                if url not in urls:
                    urls[url] = {"vendor": vendor_name, "district": "unknown", "title": ""}
    if existing_results:
        for vendor_name, vendor_data in existing_results.get("vendors", {}).items():
            for results in vendor_data.get("searches", {}).values():
                if not isinstance(results, list):
                    continue
                for r in results:
                    url = r.get("url", "")
                    if url and is_downloadable_url(url) and url not in urls:
                        text = f"{url} {r.get('title', '')} {r.get('text', '')}".lower()
                        district = "SFUSD" if "sfusd" in text else "unknown"
                        urls[url] = {"vendor": vendor_name, "district": district, "title": r.get("title", "")}
    return urls


async def download_one(session, url, metadata, sem):
    async with sem:
        vendor = metadata["vendor"]
        district = metadata["district"]

        if district == "SFUSD":
            save_dir = SFUSD_DIR
        else:
            dist_clean = sanitize_filename(district) if district != "unknown" else "other"
            save_dir = PEERS_DIR / dist_clean
        save_dir.mkdir(parents=True, exist_ok=True)

        filename = url_to_filename(url, vendor)
        save_path = save_dir / filename

        if save_path.exists() and save_path.stat().st_size > 1000:
            return url, {"url": url, "status": "already_exists", "path": str(save_path)}

        try:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=TIMEOUT),
                                   allow_redirects=True, ssl=False) as resp:
                if resp.status != 200:
                    return url, {"url": url, "status": f"http_{resp.status}"}

                content_length = resp.headers.get("Content-Length")
                if content_length and int(content_length) > MAX_FILE_SIZE:
                    return url, {"url": url, "status": "too_large", "size": int(content_length)}

                content = await resp.read()

                if len(content) > MAX_FILE_SIZE:
                    return url, {"url": url, "status": "too_large", "size": len(content)}
                if len(content) < 500:
                    return url, {"url": url, "status": "too_small", "size": len(content)}

                # Check for Cloudflare / HTML error pages
                head = content[:500]
                if b"<!DOCTYPE html" in head or b"<html" in head:
                    if b"cloudflare" in content[:2000].lower():
                        return url, {"url": url, "status": "cloudflare_blocked"}
                    if b"403 Forbidden" in head or b"Access Denied" in head:
                        return url, {"url": url, "status": "access_denied"}
                    content_type = resp.headers.get("Content-Type", "")
                    if "pdf" not in content_type.lower() and not url.lower().endswith(".pdf"):
                        return url, {"url": url, "status": "html_not_pdf"}

                save_path.write_bytes(content)
                return url, {
                    "url": url, "status": "downloaded", "path": str(save_path),
                    "size": len(content), "is_pdf": content[:5] == b'%PDF-',
                    "vendor": vendor, "district": district,
                }

        except asyncio.TimeoutError:
            return url, {"url": url, "status": "timeout"}
        except Exception as e:
            return url, {"url": url, "status": "error", "error": str(e)[:200]}


async def run_downloads(to_download):
    sem = asyncio.Semaphore(CONCURRENCY)
    connector = aiohttp.TCPConnector(limit=CONCURRENCY, ssl=False)
    async with aiohttp.ClientSession(headers=HEADERS, connector=connector) as session:
        tasks = [download_one(session, url, meta, sem) for url, meta in to_download.items()]
        results = {}
        done = 0
        ok = 0
        fail = 0
        for coro in asyncio.as_completed(tasks):
            url, result = await coro
            results[url] = result
            done += 1
            status = result["status"]
            if status == "downloaded":
                ok += 1
                size_kb = result.get("size", 0) / 1024
                print(f"  [{done}/{len(tasks)}] OK ({size_kb:.0f}KB): {result.get('vendor', '?')[:30]}", flush=True)
            elif status != "already_exists":
                fail += 1
                if done <= 200 or done % 50 == 0:  # Don't spam failures
                    print(f"  [{done}/{len(tasks)}] {status}: {url[:70]}...", flush=True)
            if done % 100 == 0:
                print(f"  --- Progress: {done}/{len(tasks)} | {ok} downloaded, {fail} failed ---", flush=True)
        return results


def main():
    peer_contracts = None
    if PEER_CONTRACTS_PATH.exists():
        with open(PEER_CONTRACTS_PATH) as f:
            peer_contracts = json.load(f)
        print(f"Loaded peer_contracts.json: {len(peer_contracts)} vendors", flush=True)

    existing_results = None
    if EXISTING_RESULTS_PATH.exists():
        with open(EXISTING_RESULTS_PATH) as f:
            existing_results = json.load(f)
        print(f"Loaded vendor_research_results.json", flush=True)

    urls = collect_urls(peer_contracts, existing_results)
    print(f"Found {len(urls)} downloadable URLs", flush=True)

    # Load existing manifest for resume
    manifest = {}
    if MANIFEST_PATH.exists():
        with open(MANIFEST_PATH) as f:
            manifest = json.load(f)

    to_download = {url: meta for url, meta in urls.items()
                   if url not in manifest or manifest[url].get("status") in ("error", "timeout")}

    print(f"To download: {len(to_download)} ({len(urls) - len(to_download)} already processed)", flush=True)
    print(f"Concurrency: {CONCURRENCY} simultaneous connections", flush=True)

    if not to_download:
        print("Nothing to do.", flush=True)
    else:
        results = asyncio.run(run_downloads(to_download))
        manifest.update(results)
        with open(MANIFEST_PATH, 'w') as f:
            json.dump(manifest, f, indent=2)

    # Summary
    statuses = {}
    for v in manifest.values():
        s = v.get("status", "?")
        statuses[s] = statuses.get(s, 0) + 1

    print(f"\n{'='*60}", flush=True)
    print(f"DOWNLOAD COMPLETE", flush=True)
    print(f"{'='*60}", flush=True)
    for s, c in sorted(statuses.items(), key=lambda x: -x[1]):
        print(f"  {s}: {c}", flush=True)

    sfusd_count = len(list(SFUSD_DIR.glob("*.pdf"))) if SFUSD_DIR.exists() else 0
    peer_dirs = list(PEERS_DIR.iterdir()) if PEERS_DIR.exists() else []
    peer_count = sum(len(list(d.glob("*.pdf"))) for d in peer_dirs if d.is_dir())
    print(f"\nOn disk: {sfusd_count} SFUSD PDFs, {peer_count} peer PDFs", flush=True)

    cf_blocked = [url for url, r in manifest.items() if r.get("status") == "cloudflare_blocked"]
    if cf_blocked:
        print(f"\n{len(cf_blocked)} URLs blocked by Cloudflare", flush=True)
        with open(DATA_DIR / "cloudflare_blocked_urls.json", 'w') as f:
            json.dump(cf_blocked, f, indent=2)

    print(f"\nManifest: {MANIFEST_PATH}", flush=True)


if __name__ == "__main__":
    main()

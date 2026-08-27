#!/usr/bin/env python3
"""Verify all BibTeX references: check DOIs via Crossref API, URLs via HTTP HEAD."""
import re
import json
import urllib.request
import urllib.error
import ssl
import sys
import time

BIB_FILE = "/Users/e.baena/lunar_paper/references.bib"

def parse_bib(content):
    """Parse bib entries into list of dicts."""
    entries = []
    # Split on @ at start of line
    raw_entries = re.split(r'\n(?=@)', content)
    for raw in raw_entries:
        raw = raw.strip()
        if not raw or not raw.startswith('@'):
            continue
        # Extract key
        key_match = re.match(r'@(\w+)\{([^,]+),', raw)
        if not key_match:
            continue
        entry_type = key_match.group(1)
        key = key_match.group(2).strip()
        
        # Extract fields
        def extract_field(name):
            pattern = rf'{name}\s*=\s*\{{([^}}]+)\}}'
            m = re.search(pattern, raw, re.IGNORECASE)
            return m.group(1).strip() if m else ''
        
        entry = {
            'type': entry_type,
            'key': key,
            'doi': extract_field('doi'),
            'url': extract_field('url'),
            'title': extract_field('title'),
            'author': extract_field('author'),
            'year': extract_field('year'),
            'journal': extract_field('journal'),
            'note': extract_field('note'),
            'raw': raw,
        }
        entries.append(entry)
    return entries

def check_doi_crossref(doi):
    """Check DOI via Crossref API. Returns (status, details)."""
    url = f"https://api.crossref.org/works/{doi}"
    req = urllib.request.Request(url, headers={
        'User-Agent': 'RefChecker/1.0 (mailto:check@example.org)',
        'Accept': 'application/json'
    })
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())
            msg = data.get('message', {})
            cr_title = ''
            if msg.get('title'):
                cr_title = msg['title'][0] if isinstance(msg['title'], list) else msg['title']
            cr_authors = []
            for a in msg.get('author', []):
                name = f"{a.get('given', '')} {a.get('family', '')}".strip()
                if name:
                    cr_authors.append(name)
            cr_year = ''
            for date_field in ['published-print', 'published-online', 'created']:
                if date_field in msg and msg[date_field].get('date-parts'):
                    parts = msg[date_field]['date-parts'][0]
                    if parts:
                        cr_year = str(parts[0])
                        break
            return ('OK', {
                'title': cr_title,
                'authors': cr_authors[:3],
                'year': cr_year,
                'container': msg.get('container-title', [''])[0] if msg.get('container-title') else '',
            })
    except urllib.error.HTTPError as e:
        return (f"HTTP_{e.code}", str(e))
    except Exception as e:
        return (f"ERROR", str(e))

def check_url(url):
    """Check if URL is accessible via HTTP HEAD."""
    # Skip non-http URLs
    if not url.startswith('http://') and not url.startswith('https://'):
        return ('SKIP', 'non-http')
    req = urllib.request.Request(url, headers={
        'User-Agent': 'Mozilla/5.0 (RefChecker)',
    }, method='HEAD')
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return (f"OK_{resp.status}", resp.url)
    except urllib.error.HTTPError as e:
        return (f"HTTP_{e.code}", str(e))
    except Exception as e:
        # Try GET as fallback (some servers don't support HEAD)
        try:
            req2 = urllib.request.Request(url, headers={
                'User-Agent': 'Mozilla/5.0 (RefChecker)',
            })
            with urllib.request.urlopen(req2, timeout=15) as resp:
                return (f"OK_{resp.status}", resp.url)
        except urllib.error.HTTPError as e:
            return (f"HTTP_{e.code}", str(e))
        except Exception as e2:
            return (f"ERROR", str(e2))

def main():
    with open(BIB_FILE, 'r') as f:
        content = f.read()
    
    entries = parse_bib(content)
    print(f"Total entries: {len(entries)}")
    print("=" * 80)
    
    results = []
    
    for i, entry in enumerate(entries):
        key = entry['key']
        doi = entry['doi']
        url = entry['url']
        title = entry['title'][:60]
        
        status_parts = []
        details = {}
        
        # Check DOI
        if doi:
            doi_status, doi_info = check_doi_crossref(doi)
            status_parts.append(f"DOI:{doi_status}")
            details['doi_info'] = doi_info
            
            if doi_status == 'OK':
                # Compare metadata
                cr = doi_info
                issues = []
                
                # Check title similarity
                if title and cr['title']:
                    # Simple word overlap check
                    bib_words = set(re.findall(r'\w+', title.lower())) - {'the', 'a', 'an', 'of', 'for', 'in', 'on', 'and', 'to'}
                    cr_words = set(re.findall(r'\w+', cr['title'][:80].lower())) - {'the', 'a', 'an', 'of', 'for', 'in', 'on', 'and', 'to'}
                    overlap = bib_words & cr_words
                    if len(bib_words) > 0 and len(overlap) / len(bib_words) < 0.3:
                        issues.append(f"TITLE MISMATCH: bib='{title}' vs crossref='{cr['title'][:60]}'")
                
                # Check year
                if entry['year'] and cr['year'] and entry['year'] != cr['year']:
                    issues.append(f"YEAR MISMATCH: bib={entry['year']} vs crossref={cr['year']}")
                
                if issues:
                    status_parts.append("META_ISSUES")
                    details['issues'] = issues
            time.sleep(0.5)  # Rate limit
        else:
            status_parts.append("DOI:NONE")
        
        # Check URL if no DOI, or if DOI failed
        if url and (not doi or 'OK' not in str(doi_status)):
            url_status, url_info = check_url(url)
            status_parts.append(f"URL:{url_status}")
            details['url_info'] = url_info
            time.sleep(0.3)
        elif url:
            status_parts.append("URL:SKIPPED(has DOI)")
        
        status = " | ".join(status_parts)
        results.append((key, status, details, entry))
        
        # Print progress
        issue_flag = " *** ISSUE ***" if "MISMATCH" in status or "HTTP_4" in status or "HTTP_5" in status or "ERROR" in status or "META_ISSUES" in status else ""
        print(f"[{i+1}/{len(entries)}] {key}: {status}{issue_flag}")
        
        if issue_flag and details.get('issues'):
            for iss in details['issues']:
                print(f"    -> {iss}")
    
    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    
    ok_count = sum(1 for _, s, _, _ in results if "OK" in s and "MISMATCH" not in s and "META_ISSUES" not in s)
    issue_count = sum(1 for _, s, _, _ in results if "MISMATCH" in s or "HTTP_4" in s or "HTTP_5" in s or "META_ISSUES" in s)
    error_count = sum(1 for _, s, _, _ in results if "ERROR" in s and "OK" not in s)
    no_doi_count = sum(1 for _, s, _, _ in results if "DOI:NONE" in s)
    
    print(f"OK: {ok_count}")
    print(f"ISSUES (mismatch/404/500): {issue_count}")
    print(f"ERRORS: {error_count}")
    print(f"No DOI: {no_doi_count}")
    
    if issue_count > 0 or error_count > 0:
        print("\n" + "-" * 40)
        print("ENTRIES WITH ISSUES:")
        print("-" * 40)
        for key, status, details, entry in results:
            if "MISMATCH" in status or "HTTP_4" in status or "HTTP_5" in status or "META_ISSUES" in status or ("ERROR" in status and "OK" not in status):
                print(f"\n{key}: {status}")
                if details.get('issues'):
                    for iss in details['issues']:
                        print(f"  {iss}")
                print(f"  Title: {entry['title'][:80]}")
                print(f"  Author: {entry['author'][:60]}")
                print(f"  Year: {entry['year']}")
                if entry['doi']:
                    print(f"  DOI: {entry['doi']}")
                if entry['url']:
                    print(f"  URL: {entry['url'][:80]}")

if __name__ == '__main__':
    main()

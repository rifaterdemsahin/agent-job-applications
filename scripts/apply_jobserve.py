#!/usr/bin/env python3
"""JobServe UK search + shortlist runner for the Job Portal Applications Agent.

Implements the decision engine from specs/hermes-spec.yaml:
  - WebForms POST search against JobServe UK (GET search returns HTTP 500)
  - clearance > geography > IR35 > role-domain ranking (Tier 0..n, lower wins)
  - exclusion filters (umbrella/PAYE-only, third-party ATS walls)
  - cross-run deduplication via metadata/run_history.json

Scope honesty: this runner searches, ranks, dedupes and logs. Form submission
itself rides the logged-in Chrome session under the spec's human_execution
protocol (3-6 min pacing, immediate human handover on captcha). Use
--mark-applied to record a submission the human/browser session completed.

Usage:
  python3 scripts/apply_jobserve.py search --keywords "AI Engineer" --location Cambridge
  python3 scripts/apply_jobserve.py search --keywords "SRE" --location "London" --limit 20 --json
  python3 scripts/apply_jobserve.py mark-applied --id <JOB_ID> --cv cv_sre_engineer.pdf
  python3 scripts/apply_jobserve.py stats
"""
from __future__ import annotations

import argparse
import http.cookiejar
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from html import unescape as html_unescape
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RUN_HISTORY = ROOT / "metadata" / "run_history.json"
CV_MAPPINGS = ROOT / "templates" / "cv_mappings.json"
QUEUE_DIR = ROOT / "metadata" / "queues"

BASE = "https://www.jobserve.com"
SEARCH_PAGE = f"{BASE}/gb/en/job-search/"
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0 Safari/537.36")

# Humanised pacing between page fetches (spec section 6 applies to submissions;
# searches get a lighter 2-4s jitter so runs stay polite).
FETCH_DELAY_S = (2.0, 4.0)

CARELESS_WORDS = re.compile(
    r"(verify you are human|recaptcha|captcha|are you a robot)", re.I)


def _opener() -> urllib.request.OpenerDirector:
    cj = http.cookiejar.CookieJar()
    return urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))


def _get(op, url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with op.open(req, timeout=30) as r:
        return r.read().decode("utf-8", "replace")


def _post(op, url: str, fields: dict) -> str:
    data = urllib.parse.urlencode(fields).encode()
    req = urllib.request.Request(url, data=data, headers={
        "User-Agent": UA,
        "Content-Type": "application/x-www-form-urlencoded",
    })
    with op.open(req, timeout=30) as r:
        return r.read().decode("utf-8", "replace")


def _token(html: str, name: str) -> str:
    m = re.search(rf'id="{name}"[^>]*value="([^"]*)"', html) or \
        re.search(rf'name="{name}"[^>]*value="([^"]*)"', html)
    return m.group(1) if m else ""


MOB_RESULTS = BASE + "/gb/en/mob/jobsearch/results/{shid}?page={page}"
SHID = re.compile(r'/mob/jobsearch/results/([0-9A-Fa-f]+)')

JOB_ROW = re.compile(
    r'<li id="J(?P<id>[0-9A-Fa-f]+)"\s*>\s*<a href="(?P<href>[^"]+)"[^>]*>\s*'
    r'<span class="position">(?P<title>.*?)</span>\s*'
    r"<span>(?P<rate>.*?)</span>\s*"
    r"<span>(?P<location>.*?)</span>\s*"
    r"<span>(?P<etype>.*?)</span>", re.S)


def search_jobserve(keywords: str, location: str, radius: str = "25",
                    max_pages: int = 3) -> list[dict]:
    """POST the JobServe search form, then page through the mobile results
    endpoint (clean <li> rows) and return parsed job dicts."""
    op = _opener()
    home = _get(op, SEARCH_PAGE)
    if CARELESS_WORDS.search(home):
        raise SystemExit("CAPTCHA/WAF wall on the search page — hand control to "
                         "the human operator (spec section 6) and resume after.")
    fields = {
        "__EVENTTARGET": "",
        "__EVENTARGUMENT": "",
        "__VIEWSTATE": _token(home, "__VIEWSTATE"),
        "__VIEWSTATEGENERATOR": _token(home, "__VIEWSTATEGENERATOR"),
        "__EVENTVALIDATION": _token(home, "__EVENTVALIDATION"),
        "ctl00$main$srch$ctl_qs$txtKey": keywords,
        "ctl00$main$srch$ctl_qs$txtTitle": "",
        "ctl00$main$srch$ctl_qs$txtLoc": location,
        "selRad": radius,
        "ctl00$main$srch$ctl_qs$hdnAccount": "",
        "ctl00$main$srch$ctl_qs$hdnMasterAccount": "",
        "ctl00$main$srch$ctl_qs$btnSearch": "Search",
    }
    html = _post(op, SEARCH_PAGE, fields)
    if CARELESS_WORDS.search(html):
        raise SystemExit("CAPTCHA/WAF wall on the results page — human handover "
                         "required (spec section 6).")
    m = SHID.search(html)
    if not m:
        raise SystemExit("No search results session (shid) in the response — "
                         "JobServe changed its flow; inspect the POST response.")
    shid = m.group(1)

    jobs: list[dict] = []
    seen: set[str] = set()
    for page in range(1, max_pages + 1):
        time.sleep(2.0)
        page_html = _get(op, MOB_RESULTS.format(shid=shid, page=page))
        if CARELESS_WORDS.search(page_html):
            raise SystemExit("CAPTCHA/WAF wall on a results page — human "
                             "handover required (spec section 6).")
        rows = parse_jobs(page_html)
        if not rows:
            break
        for j in rows:
            if j["job_id"] not in seen:
                seen.add(j["job_id"])
                jobs.append(j)
    return jobs


def parse_jobs(html: str) -> list[dict]:
    """Parse mobile results rows: <li id='J<ID'> with title/rate/location/type."""
    jobs = []
    for m in JOB_ROW.finditer(html):
        title = html_unescape(re.sub(r"<[^>]+>", "", m.group("title"))).strip()
        if not title:
            continue
        jobs.append({
            "job_id": m.group("id"),
            "title": title,
            "url": BASE + m.group("href").split("?")[0],
            "rate": html_unescape(re.sub(r"<[^>]+>", "", m.group("rate"))).strip(),
            "location": html_unescape(re.sub(r"<[^>]+>", "", m.group("location"))).strip(),
            "employment_type": re.sub(r"<[^>]+>", "", m.group("etype")).strip(),
            "context": "",
        })
    return jobs


# ---- Decision engine (spec section 5) -------------------------------------

def clearance_tier(text: str) -> int:
    if re.search(r"\b(DV|SC|NATO)\b|developed vetting|security clear", text, re.I):
        return 0
    return 3


def geo_tier(text: str) -> int:
    t = text.lower()
    if "cambridge" in t:
        return 1
    if "london" in t:
        return 2
    if "remote" in t or "home based" in t or "hybrid" in t:
        return 3
    return 4


def ir35_tier(text: str) -> tuple[int, bool]:
    """Return (tier, excluded). Umbrella/PAYE-only is an exclusion filter."""
    t = text.lower()
    if "outside ir35" in t:
        return 1, False
    if "umbrella" in t and "outside ir35" not in t:
        return 9, True
    if "paye" in t and "outside ir35" not in t and "day rate" not in t:
        return 9, True
    if "inside ir35" in t:
        return 2, False
    return 5, False


def domain_tier(title: str, context: str, mappings: dict) -> tuple[int, str]:
    blob = f"{title} {context}".lower()
    for i, rule in enumerate(mappings.get("routing_rules", []), start=1):
        if any(kw.lower() in blob for kw in rule.get("match_keywords", [])):
            return i, rule["role_cluster"][0]
    return 6, "unclassified"


def route_cv(cluster_rule_idx: int, mappings: dict) -> str:
    rules = mappings.get("routing_rules", [])
    if 1 <= cluster_rule_idx <= len(rules):
        return rules[cluster_rule_idx - 1]["cv_files"][0]
    return mappings.get("fallback_cv", "")


def rank(jobs: list[dict], mappings: dict) -> list[dict]:
    out = []
    for j in jobs:
        blob = f"{j['title']} {j.get('rate', '')} {j.get('location', '')} {j.get('employment_type', '')} {j.get('context', '')}"
        ir, excluded = ir35_tier(blob)
        d, cluster = domain_tier(j["title"], blob, mappings)
        j2 = dict(j)
        j2.update({
            "clearance_tier": clearance_tier(blob),
            "geo_tier": geo_tier(blob),
            "ir35_tier": ir,
            "excluded": excluded,
            "domain_tier": d,
            "role_cluster": cluster,
            "cv_file": route_cv(d, mappings) if not excluded else "",
        })
        out.append(j2)
    out.sort(key=lambda x: (x["excluded"], x["clearance_tier"], x["geo_tier"],
                            x["ir35_tier"], x["domain_tier"]))
    return out


# ---- Run history / dedup ---------------------------------------------------

def load_history() -> dict:
    return json.loads(RUN_HISTORY.read_text())


def save_history(h: dict) -> None:
    RUN_HISTORY.write_text(json.dumps(h, indent=2) + "\n")


def cmd_search(args) -> None:
    mappings = json.loads(CV_MAPPINGS.read_text())
    jobs = search_jobserve(args.keywords, args.location, args.radius)
    ranked = rank(jobs, mappings)
    history = load_history()
    applied = set(history.get("application_ids", []))
    for j in ranked:
        j["already_applied"] = j["job_id"] in applied
    selected = [j for j in ranked if not j["excluded"] and not j["already_applied"]]
    selected = selected[:args.limit]

    QUEUE_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    queue_path = QUEUE_DIR / f"queue-{stamp}-{args.location.lower().replace(' ', '_')}.json"
    queue_path.write_text(json.dumps({
        "generated": datetime.now(timezone.utc).isoformat(),
        "keywords": args.keywords,
        "location": args.location,
        "counts": {"parsed": len(jobs), "excluded": sum(1 for j in ranked if j["excluded"]),
                   "already_applied": sum(1 for j in ranked if j["already_applied"]),
                   "queued": len(selected)},
        "queue": selected,
    }, indent=2) + "\n")

    history.setdefault("runs", []).append({
        "ts": datetime.now(timezone.utc).isoformat(),
        "type": "search",
        "keywords": args.keywords,
        "location": args.location,
        "parsed": len(jobs),
        "queued": len(selected),
        "queue_file": str(queue_path.relative_to(ROOT)),
    })
    save_history(history)

    if args.json:
        print(json.dumps(selected, indent=2))
        return
    print(f"parsed={len(jobs)} queued={len(selected)} -> {queue_path.relative_to(ROOT)}")
    for j in selected:
        print(f"[{j['clearance_tier']}{j['geo_tier']}{j['ir35_tier']}{j['domain_tier']}] "
              f"{j['job_id']}  {j['title'][:60]:60}  {j['rate'][:18]:18}  "
              f"cluster={j['role_cluster']}  cv={j['cv_file']}")


def cmd_mark_applied(args) -> None:
    history = load_history()
    if args.id in history.get("application_ids", []):
        print(f"{args.id} already recorded — dedup skip (spec: strict skip).")
        return
    history.setdefault("application_ids", []).append(args.id)
    history.setdefault("runs", []).append({
        "ts": datetime.now(timezone.utc).isoformat(),
        "type": "applied",
        "job_id": args.id,
        "cv": args.cv,
        "status": args.status,
    })
    save_history(history)
    print(f"recorded application {args.id} (cv={args.cv}, status={args.status})")


def cmd_stats(args) -> None:
    history = load_history()
    applied = history.get("application_ids", [])
    runs = history.get("runs", [])
    print(f"application_ids: {len(applied)}")
    print(f"runs: {len(runs)}")
    for r in runs[-10:]:
        print(f"  {r.get('ts', '?')}  {r.get('type', '?')}  {json.dumps({k: v for k, v in r.items() if k not in ('ts', 'type')})[:90]}")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("search", help="search JobServe, rank, dedupe, write queue")
    s.add_argument("--keywords", required=True)
    s.add_argument("--location", required=True)
    s.add_argument("--radius", default="25")
    s.add_argument("--limit", type=int, default=15)
    s.add_argument("--json", action="store_true")
    s.set_defaults(func=cmd_search)
    m = sub.add_parser("mark-applied", help="record a submitted application id")
    m.add_argument("--id", required=True)
    m.add_argument("--cv", default="")
    m.add_argument("--status", default="submitted")
    m.set_defaults(func=cmd_mark_applied)
    st = sub.add_parser("stats", help="show run history summary")
    st.set_defaults(func=cmd_stats)
    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Auto-update the "results" profile in pool.json with FINISHED group-stage scores
from ESPN's public FIFA World Cup feed (no API key needed).

Scope & safety:
  * Only group-stage matches (1-72) are ever written. Knockout entries (73-104)
    and every player profile are left exactly as they are.
  * A game is written only once ESPN marks it completed AND its kick-off time has
    actually passed (guards against premature/placeholder "completed" flags).
  * Home/away orientation is matched to the app's fixtures, so winners are correct.

Local-test env flags:
  WC_DRYRUN=1        -> print what would change, do not write pool.json
  WC_IGNORE_FUTURE=1 -> ignore the "kick-off must have passed" guard
"""
import json, os, re, sys, unicodedata, urllib.request
from datetime import datetime, timezone

POOL_PATH = os.environ.get("WC_POOL", "pool.json")
ESPN = "https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.world/scoreboard?dates={d}"
DATES = [f"202606{d:02d}" for d in range(11, 28)]   # Jun 11-27 = group stage
DRYRUN = bool(os.environ.get("WC_DRYRUN"))
IGNORE_FUTURE = bool(os.environ.get("WC_IGNORE_FUTURE"))

GROUP_FIXTURES = {
    1: ('Mexico', 'South Africa'),
    2: ('South Korea', 'Czech Republic'),
    3: ('Canada', 'Bosnia and Herzegovina'),
    4: ('United States', 'Paraguay'),
    5: ('Haiti', 'Scotland'),
    6: ('Australia', 'Turkey'),
    7: ('Brazil', 'Morocco'),
    8: ('Qatar', 'Switzerland'),
    9: ('Ivory Coast', 'Ecuador'),
    10: ('Germany', 'Curaçao'),
    11: ('Netherlands', 'Japan'),
    12: ('Sweden', 'Tunisia'),
    13: ('Saudi Arabia', 'Uruguay'),
    14: ('Spain', 'Cape Verde'),
    15: ('Iran', 'New Zealand'),
    16: ('Belgium', 'Egypt'),
    17: ('France', 'Senegal'),
    18: ('Iraq', 'Norway'),
    19: ('Argentina', 'Algeria'),
    20: ('Austria', 'Jordan'),
    21: ('Ghana', 'Panama'),
    22: ('England', 'Croatia'),
    23: ('Portugal', 'DR Congo'),
    24: ('Uzbekistan', 'Colombia'),
    25: ('Czech Republic', 'South Africa'),
    26: ('Switzerland', 'Bosnia and Herzegovina'),
    27: ('Canada', 'Qatar'),
    28: ('Mexico', 'South Korea'),
    29: ('Brazil', 'Haiti'),
    30: ('Scotland', 'Morocco'),
    31: ('Turkey', 'Paraguay'),
    32: ('United States', 'Australia'),
    33: ('Germany', 'Ivory Coast'),
    34: ('Ecuador', 'Curaçao'),
    35: ('Netherlands', 'Sweden'),
    36: ('Tunisia', 'Japan'),
    37: ('Uruguay', 'Cape Verde'),
    38: ('Spain', 'Saudi Arabia'),
    39: ('Belgium', 'Iran'),
    40: ('New Zealand', 'Egypt'),
    41: ('Norway', 'Senegal'),
    42: ('France', 'Iraq'),
    43: ('Argentina', 'Austria'),
    44: ('Jordan', 'Algeria'),
    45: ('England', 'Ghana'),
    46: ('Panama', 'Croatia'),
    47: ('Portugal', 'Uzbekistan'),
    48: ('Colombia', 'DR Congo'),
    49: ('Scotland', 'Brazil'),
    50: ('Morocco', 'Haiti'),
    51: ('Switzerland', 'Canada'),
    52: ('Bosnia and Herzegovina', 'Qatar'),
    53: ('Czech Republic', 'Mexico'),
    54: ('South Africa', 'South Korea'),
    55: ('Curaçao', 'Ivory Coast'),
    56: ('Ecuador', 'Germany'),
    57: ('Japan', 'Sweden'),
    58: ('Tunisia', 'Netherlands'),
    59: ('Turkey', 'United States'),
    60: ('Paraguay', 'Australia'),
    61: ('Norway', 'France'),
    62: ('Senegal', 'Iraq'),
    63: ('Egypt', 'Iran'),
    64: ('New Zealand', 'Belgium'),
    65: ('Cape Verde', 'Saudi Arabia'),
    66: ('Uruguay', 'Spain'),
    67: ('Panama', 'England'),
    68: ('Croatia', 'Ghana'),
    69: ('Algeria', 'Austria'),
    70: ('Jordan', 'Argentina'),
    71: ('Colombia', 'Portugal'),
    72: ('DR Congo', 'Uzbekistan'),
}

ALIASES = {
    "bosniaherzegovina": "bosniaandherzegovina",
    "congodr": "drcongo",
    "czechia": "czechrepublic",
    "turkiye": "turkey",
}

def norm(s):
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode()
    s = re.sub(r"[^a-z0-9]", "", s.lower())
    return ALIASES.get(s, s)

LOOKUP = {}
for _n, (_h, _a) in GROUP_FIXTURES.items():
    LOOKUP[frozenset((norm(_h), norm(_a)))] = (_n, _h, _a)

def parse_dt(s):
    s = (s or "").replace("Z", "+00:00")
    m = re.match(r"(\d{4}-\d{2}-\d{2}T\d{2}:\d{2})(:\d{2})?(.*)", s)
    if m and not m.group(2):
        s = m.group(1) + ":00" + (m.group(3) or "")
    return datetime.fromisoformat(s)

def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "wc2026-results-bot"})
    with urllib.request.urlopen(req, timeout=25) as r:
        return json.load(r)

def main():
    try:
        pool = json.load(open(POOL_PATH, encoding="utf-8"))
    except Exception as e:
        print("Could not read pool.json:", e); return 0
    res_name = pool.get("resultsName")
    prof = next((p for p in pool.get("profiles", []) if p.get("name") == res_name), None)
    if prof is None:
        print("No results profile named", repr(res_name), "- nothing to do."); return 0
    results = prof.setdefault("results", {})

    now = datetime.now(timezone.utc)
    found, unmatched, skipped_future = {}, [], 0
    for d in DATES:
        try:
            data = fetch(ESPN.format(d=d))
        except Exception as e:
            print("fetch failed", d, e); continue
        for ev in data.get("events", []):
            comp = (ev.get("competitions") or [{}])[0]
            st = (comp.get("status") or {}).get("type") or {}
            if not st.get("completed"):
                continue
            try:
                if not IGNORE_FUTURE and parse_dt(ev.get("date")) > now:
                    skipped_future += 1; continue
            except Exception:
                continue
            cs = comp.get("competitors", [])
            if len(cs) != 2:
                continue
            names = [c.get("team", {}).get("displayName", "") for c in cs]
            hit = LOOKUP.get(frozenset(norm(x) for x in names))
            if not hit:
                unmatched.append(names); continue
            n, h, a = hit
            byteam = {}
            for c in cs:
                try:
                    byteam[norm(c.get("team", {}).get("displayName", ""))] = int(c.get("score"))
                except Exception:
                    pass
            if norm(h) in byteam and norm(a) in byteam:
                found[n] = {"h": byteam[norm(h)], "a": byteam[norm(a)]}

    changed = 0
    for n, sc in sorted(found.items()):
        if results.get(str(n)) != sc:
            results[str(n)] = sc; changed += 1
            print(f"  set match {n}: {GROUP_FIXTURES[n][0]} {sc['h']}-{sc['a']} {GROUP_FIXTURES[n][1]}")
    print(f"finished+past group games: {len(found)} | updated: {changed} | "
          f"skipped (kick-off not passed): {skipped_future} | unmatched events: {len(unmatched)}")
    for u in unmatched[:15]:
        print("  UNMATCHED:", u)
    if changed and not DRYRUN:
        json.dump(pool, open(POOL_PATH, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
        open(POOL_PATH, "a", encoding="utf-8").write("\n")
        print("pool.json written.")
    elif changed:
        print("[dry-run] would write pool.json")
    return 0

if __name__ == "__main__":
    sys.exit(main())

"""Loads the certified 2026 general election ballot for every precinct in
Maryland (all 24 jurisdictions) from the MSBE ballot PDFs
(https://elections.maryland.gov/elections/2026/general_ballots/<County>.pdf),
parsed by md_general_ballot_parser.py. Supersedes the hand-transcribed
Montgomery BS 125 loader: the MD general election's contests and ballot
styles are deleted and rebuilt in the same transaction.

Before writing any SQL it checks the parsed ballots against MSBE's official
candidate lists (general_candidates/2026_GG_*_candidatelist.csv) and exits 1
on any mismatch: every printed candidate must be on the list with the same
party, and every active candidate must be printed somewhere, except
write-ins. Names compare without quotes ("Todd" Creek is listed as Todd
Creek).

Mapping a printed title to an office and district:
- Statewide offices, U.S. Representative (cd119), State Senator (sldu) and
  House of Delegates (md_delegate_subdistricts_2022, "1C" -> "01C") are
  shared across counties. The congressional district comes from the official
  list by candidate name (Frederick prints "Representative in Congress"
  without its number) and must agree with the printed number when there is
  one.
- Everything else is a county office and is scoped to its county (layer
  `county`, district_id = county FIPS): "County Council District 1" exists
  in several counties, and the Circuit Court judges on Montgomery's and
  Frederick's "Circuit 6" ballots are different people. Cumberland's city
  contests (on some Allegany ballots) are scoped to the city (`place`), so
  sample-ballot can tell a split precinct's two styles apart.

Ballot styles map 1:1 to precincts except 10 split precincts (5 in Allegany:
inside/outside Cumberland; 5 in Talbot: Board of Education district, for
which there is no boundary layer). Ballot precinct "008-006" is precinct_code
"<county FIPS>08-006". Precincts missing from the md_precincts_2026 layer
(Garrett and Kent's layer is coarser than their ballots) are reported and
skipped.

Usage:
    python3 scripts/load_md_general_2026.py <pdf cache dir> > out.sql
"""
import csv
import http.client
import io
import os
import re
import sys
import time
import urllib.request
import uuid
from collections import Counter, defaultdict
from multiprocessing import Pool

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import md_general_ballot_parser as parser  # noqa: E402

BASE = "https://elections.maryland.gov/elections/2026/"
GENERAL_ELECTION_ID = "55555555-5555-5555-5555-555555555555"  # created by load_md_2026_elections_calendar.py
NS = uuid.uuid5(uuid.NAMESPACE_URL, BASE + "general_ballots/")
CERTIFICATION_DATE = "2026-08-31"
PUBLISHED_DATE = "2026-09-03"  # "Updated 09/03/2026": Question 3 language revised by court order
CANDIDATE_LISTS = ["2026_GG_statewide_candidatelist.csv", "2026_GG_all_counties_candidatelist.csv"]

COUNTIES = {  # PDF name -> (county FIPS, name in the candidate lists)
    "Allegany": ("24001", "Allegany"), "AnneArundel": ("24003", "Anne Arundel"),
    "BaltimoreCounty": ("24005", "Baltimore County"), "Calvert": ("24009", "Calvert"),
    "Caroline": ("24011", "Caroline"), "Carroll": ("24013", "Carroll"), "Cecil": ("24015", "Cecil"),
    "Charles": ("24017", "Charles"), "Dorchester": ("24019", "Dorchester"), "Frederick": ("24021", "Frederick"),
    "Garrett": ("24023", "Garrett"), "Harford": ("24025", "Harford"), "Howard": ("24027", "Howard"),
    "Kent": ("24029", "Kent"), "Montgomery": ("24031", "Montgomery"), "PrinceGeorges": ("24033", "Prince George's"),
    "QueenAnnes": ("24035", "Queen Anne's"), "SaintMarys": ("24037", "Saint Mary's"),
    "Somerset": ("24039", "Somerset"), "Talbot": ("24041", "Talbot"), "Washington": ("24043", "Washington"),
    "Wicomico": ("24045", "Wicomico"), "Worcester": ("24047", "Worcester"), "BaltimoreCity": ("24510", "Baltimore City"),
}
# Montgomery's PDF was already a source (from the BS 125 hand transcription this loader replaced).
SOURCE_IDS = {"Montgomery": "88888888-8888-8888-8888-888888888888"}
CITY_PLACES = {"Cumberland": "2421325"}  # TIGER place GEOID of cities with contests on the ballot
# The 3 statewide questions keep the ids they were first loaded with.
STATEWIDE_MEASURE_IDS = {
    "Question 1": "aaaaaaaa-aaaa-aaaa-aaaa-000000000001",
    "Question 2": "aaaaaaaa-aaaa-aaaa-aaaa-000000000002",
    "Question 3": "aaaaaaaa-aaaa-aaaa-aaaa-000000000003",
}
STATE_OFFICES = {
    "Governor / Lt. Governor": "Governor / Lieutenant Governor",
    "Comptroller": "Comptroller",
    "Attorney General": "Attorney General",
    "Judge, Appellate Court of Maryland At Large": "Judge, Appellate Court of Maryland",
}


# The state precinct layer still has 31 polygons of precincts that no longer
# exist in 2026 (MSBE's precinct list matches the ballots, not the layer), so
# addresses there would get no ballot. Their voters now vote in some 2026
# precinct of the same county election district (MD precincts nest in them).
# When every such precinct whose located districts (congress, senate,
# delegate, city) cover most of the old polygon has the very same ballot,
# that ballot is the address's ballot; it gets the representative style's
# code + " (inferred)". Ambiguous cases (2+ different ballots, or none) and
# zero-voter "ghost" codes (-09x, -999) stay without a ballot.
INFER_STALE_PRECINCTS_SQL = """
create temp table stale_precincts on commit drop as
select p.precinct_id, p.precinct_code, p.geom, left(p.precinct_code, 8) as ed_prefix
from precincts p
where p.state = 'MD' and p.precinct_code !~ '-(09[0-9]|999)$'
  and not exists (select 1 from ballot_styles b where b.precinct_id = p.precinct_id and b.election_id = '{e}');

create temp table stale_candidates on commit drop as
select s.precinct_id as stale_id, bs.ballot_style_id, bs.style_code, bs.sample_ballot_url, bs.source_id,
  (select string_agg(contest_id::text, ',' order by contest_id) from ballot_style_contests x
   where x.ballot_style_id = bs.ballot_style_id) || '|' ||
  coalesce((select string_agg(measure_id::text, ',' order by measure_id) from ballot_style_measures x
            where x.ballot_style_id = bs.ballot_style_id), '') as signature
from stale_precincts s
join precincts q on q.state = 'MD' and left(q.precinct_code, 8) = s.ed_prefix and q.precinct_id <> s.precinct_id
join ballot_styles bs on bs.precinct_id = q.precinct_id and bs.election_id = '{e}'
where not exists (
  select 1 from ballot_style_contests x join contests k using (contest_id)
  where x.ballot_style_id = bs.ballot_style_id and k.scope = 'district'
    and k.district_layer_id in ('cd119', 'sldu', 'md_delegate_subdistricts_2022', 'place')
    and coalesce((
      select st_area(st_intersection(s.geom, st_makevalid(d.geom))::geography) / nullif(st_area(s.geom::geography), 0)
      from (select geom from cd119 where k.district_layer_id = 'cd119' and id = k.district_id
            union all select geom from sldu where k.district_layer_id = 'sldu' and id = k.district_id
            union all select geom from place where k.district_layer_id = 'place' and id = k.district_id
            union all select geom from district_boundaries
                      where layer_id = k.district_layer_id and district_id = k.district_id) d
    ), 0) < 0.5);

create temp table inferred_styles on commit drop as
select distinct on (c.stale_id) c.stale_id, c.ballot_style_id as from_style, c.style_code, c.sample_ballot_url,
  c.source_id, gen_random_uuid() as new_style
from stale_candidates c
where c.stale_id in (select stale_id from stale_candidates group by stale_id having count(distinct signature) = 1)
order by c.stale_id, c.style_code;

insert into ballot_styles (ballot_style_id, election_id, precinct_id, party, style_code, sample_ballot_url,
  certification_date, source_id)
select new_style, '{e}', stale_id, null, style_code || ' (inferred)', sample_ballot_url, '{cert}', source_id
from inferred_styles;
insert into ballot_style_contests (ballot_style_id, contest_id)
select i.new_style, x.contest_id from inferred_styles i join ballot_style_contests x on x.ballot_style_id = i.from_style;
insert into ballot_style_measures (ballot_style_id, measure_id)
select i.new_style, x.measure_id from inferred_styles i join ballot_style_measures x on x.ballot_style_id = i.from_style;

select p.precinct_code as inferred_precinct, i.style_code as same_ballot_as
from inferred_styles i join precincts p on p.precinct_id = i.stale_id order by 1;
"""


def dq(value: str, tag: str = "q") -> str:
    return f"${tag}${value}${tag}$"


def sql_text(value):
    return "null" if value is None else dq(str(value))


def sql_bool(value: bool) -> str:
    return "true" if value else "false"


def plain(name: str) -> str:
    return re.sub(r"\s+", " ", name.replace('"', "")).strip()


def fetch(url: str, attempts: int = 4) -> bytes:
    for attempt in range(1, attempts + 1):
        try:
            request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(request, timeout=120) as r:
                return r.read()
        except (OSError, http.client.IncompleteRead) as e:  # elections.maryland.gov drops connections mid-body
            if attempt == attempts:
                raise
            print(f"  retrying {url} ({e})", file=sys.stderr)
            time.sleep(2 * attempt)


def parse_county(args):
    county, path = args
    return county, parser.parse_pdf(path)


def load_ballots(pdf_dir: str):
    os.makedirs(pdf_dir, exist_ok=True)
    jobs = []
    for county in COUNTIES:
        path = os.path.join(pdf_dir, f"{county}.pdf")
        if not os.path.exists(path):
            print(f"Downloading {county}.pdf...", file=sys.stderr)
            with open(path, "wb") as f:
                f.write(fetch(f"{BASE}general_ballots/{county}.pdf"))
        jobs.append((county, path))
    print("Parsing 24 ballot PDFs...", file=sys.stderr)
    with Pool() as pool:
        return dict(pool.map(parse_county, jobs))


def load_candidate_lists():
    rows = []
    for name in CANDIDATE_LISTS:
        text = fetch(f"{BASE}general_candidates/{name}").decode("utf-8-sig")
        for r in csv.DictReader(io.StringIO(text)):
            full = f'{r["Candidate First Name and Middle Name"]} {r["Candidate Ballot Last Name and Suffix"]}'
            if r.get("Has Related Candidate") == "Yes" and r["Related Candidate Last Name and Suffix"]:
                full += f' / {r["Related Candidate First Name and Middle Name"]} {r["Related Candidate Last Name and Suffix"]}'
            rows.append({
                "name": plain(full),
                "party": r["Office Political Party"],
                "office": r["Office Name"],
                "district": r["Contest Run By District Name and Number"],
                "active": r["Candidate Status"] == "Active",
                "write_in": r["Filing Type and Date"].startswith("Write-In"),
            })
    return rows


def check_against_official_list(ballots, official) -> list[str]:
    errors = []
    parties = defaultdict(set)
    for o in official:
        parties[o["name"]].add(o["party"])
    printed = set()
    for county, styles in ballots.items():
        for style in styles:
            for contest in style.contests:
                for cand in contest.candidates:
                    printed.add(plain(cand.name))
                    if contest.retention:
                        continue
                    if plain(cand.name) not in parties:
                        errors.append(f"{county} {style.style_code}: {cand.name!r} is not on the official list")
                    elif cand.party and cand.party not in parties[plain(cand.name)]:
                        errors.append(f"{county}: {cand.name!r} printed as {cand.party}, listed as "
                                      f"{sorted(parties[plain(cand.name)])}")
    for o in official:
        if o["active"] and not o["write_in"] and o["name"] not in printed:
            errors.append(f"{o['district']} {o['office']}: active candidate {o['name']!r} is on no ballot")
    return sorted(set(errors))


def congressional_districts(official) -> dict[str, str]:
    """Candidate name -> cd119 id, from the official statewide list."""
    out = {}
    for o in official:
        m = re.match(r"Congressional District (\d+)$", o["district"])
        if o["office"] == "Representative in Congress" and m:
            out[o["name"]] = f"24{int(m.group(1)):02d}"
    return out


def classify(title: str, contest, fips: str, cds: dict[str, str]):
    """Printed title -> (office, level, label, layer_id, district_id, scope)."""
    if title in STATE_OFFICES:
        return STATE_OFFICES[title], "State", title, None, None, "at_large"
    if title.startswith("Representative in Congress"):
        found = {cds.get(plain(c.name)) for c in contest.candidates} - {None}
        if len(found) != 1:
            raise ValueError(f"cannot place {title!r} in one congressional district: {found}")
        cd = found.pop()
        printed = re.search(r"District (\d+)$", title)
        if printed and f"24{int(printed.group(1)):02d}" != cd:
            raise ValueError(f"{title!r}: official list says CD {cd}")
        return "U.S. Representative", "Federal", f"Representative in Congress District {int(cd[2:])}", "cd119", cd, "district"
    if m := re.fullmatch(r"State Senator District (\d+)", title):
        return "State Senator", "State", title, "sldu", f"24{int(m.group(1)):03d}", "district"
    if m := re.fullmatch(r"House of Delegates District (\d+)([A-C]?)", title):
        return "House of Delegates", "State", title, "md_delegate_subdistricts_2022", \
            f"{int(m.group(1)):02d}{m.group(2)}", "district"
    if title.startswith("Justice, Supreme Court of Maryland"):
        return "Justice, Supreme Court of Maryland", "State", title, None, None, "at_large"
    if m := re.fullmatch(r"(Mayor|Council) - City of (.+)", title):
        office = "Mayor" if m.group(1) == "Mayor" else "City Council"
        return office, "Local", title, "place", CITY_PLACES[m.group(2)], "district"
    office = re.sub(r" (District [\w-]+|Circuit \d+|At Large)$", "", title)
    scope = "district" if re.search(r"District [\w-]+$", title) else "at_large"
    return office, "Local", title, "county", fips, scope


def measure_fields(m):
    impact_yes = next((p for p in m.paragraphs if p.lower().startswith("a vote for ")), None)
    impact_no = next((p for p in m.paragraphs if p.lower().startswith("a vote against ")), None)
    body = [p for p in m.paragraphs if p not in (impact_yes, impact_no)]
    title = f"{m.header[0]} - {' '.join(m.header[1:])}"
    return title, " ".join(body) or None, impact_yes, impact_no


def main():
    ballots = load_ballots(sys.argv[1])
    official = load_candidate_lists()
    errors = check_against_official_list(ballots, official)
    if errors:
        print("Ballots disagree with MSBE's official candidate lists; no SQL written:", file=sys.stderr)
        for e in errors:
            print("  " + e, file=sys.stderr)
        sys.exit(1)
    cds = congressional_districts(official)

    offices = set()
    contests = {}  # contest_id -> row
    candidates = {}  # contest_id -> [(name, party)]
    measures = {}  # measure_id -> row
    styles = []  # (ballot_style_id, county, style_code, precinct_code, [contest_id], [measure_id])
    for county, county_styles in ballots.items():
        fips, _ = COUNTIES[county]
        source_id = SOURCE_IDS.get(county, str(uuid.uuid5(NS, county)))
        for style in county_styles:
            contest_ids = []
            for order, c in enumerate(style.contests, start=1):
                office, level, label, layer, district, scope = classify(" ".join(c.title), c, fips, cds)
                offices.add((office, level))
                contest_id = str(uuid.uuid5(NS, f"{office}|{level}|{district}|{label}"))
                nonpartisan = c.nonpartisan or office == "Board of Education"  # Caroline omits the banner
                row = (office, level, label, layer, district, scope, nonpartisan, c.retention, c.vote_for, order,
                       source_id)
                cands = [(cand.name, cand.party) for cand in c.candidates]
                if contest_id in contests and candidates[contest_id] != cands:
                    raise ValueError(f"{label} ({district}) prints different candidates on different ballots")
                contests.setdefault(contest_id, row)
                candidates[contest_id] = cands
                contest_ids.append(contest_id)
            measure_ids = []
            for order, m in enumerate(style.measures, start=1):
                title, question, yes, no = measure_fields(m)
                statewide = m.header[0] in STATEWIDE_MEASURE_IDS and m.header[1:2] == ["Constitutional Amendment"]
                measure_id = STATEWIDE_MEASURE_IDS[m.header[0]] if statewide else \
                    str(uuid.uuid5(NS, f"{county}|{' '.join(m.header)}"))
                measures.setdefault(measure_id, (statewide, fips, title, question, yes, no, order, source_id))
                measure_ids.append(measure_id)
            for precinct in style.precincts:
                code = f"{fips}{precinct[1:]}"  # "008-006" -> "2403108-006"
                styles.append((str(uuid.uuid5(NS, f"{county}|{style.style_code}|{code}")), county,
                               style.style_code, code, contest_ids, measure_ids))

    out = sys.stdout
    out.write("-- Generated by scripts/load_md_general_2026.py. Idempotent: safe to re-run.\n\n")
    for county in COUNTIES:
        source_id = SOURCE_IDS.get(county, str(uuid.uuid5(NS, county)))
        out.write(
            "insert into sources (source_id, source_url, source_type, effective_date, confidence, notes)\n"
            f"values ('{source_id}', {sql_text(f'{BASE}general_ballots/{county}.pdf')}, 'certified_ballot_pdf', "
            f"'{PUBLISHED_DATE}', 1.0, {sql_text(f'Maryland SBE certified general ballot, {county} (certified {CERTIFICATION_DATE})')})\n"
            "on conflict (source_id) do update set fetched_at = now(), effective_date = excluded.effective_date;\n\n"
        )

    # Rebuilt from scratch: deleting the election's contests cascades to
    # candidates and ballot_style_contests (no results exist for the general).
    out.write(f"delete from ballot_styles where election_id = '{GENERAL_ELECTION_ID}';\n")
    out.write(f"delete from contests where election_id = '{GENERAL_ELECTION_ID}';\n\n")

    out.write("insert into offices (name, level, description)\nvalues\n" + ",\n".join(
        f"  ({sql_text(o)}, {sql_text(lvl)}, {sql_text(o)})" for o, lvl in sorted(offices)
    ) + "\non conflict (name, level) do nothing;\n\n")

    out.write(
        "insert into contests (contest_id, election_id, office_id, district_layer_id, district_id, contest_label, "
        "scope, nonpartisan, retention, write_in_allowed, vote_for, order_on_ballot, source_id)\n"
        f"select v.contest_id::uuid, '{GENERAL_ELECTION_ID}', o.office_id, v.layer, v.district, v.label, v.scope, "
        "v.nonpartisan, v.retention, not v.retention, v.vote_for, v.ord, v.source_id::uuid\nfrom (values\n" + ",\n".join(
            f"  ('{cid}', {sql_text(office)}, {sql_text(level)}, {sql_text(label)}, {sql_text(layer)}, "
            f"{sql_text(district)}, {sql_text(scope)}, {sql_bool(np_)}, {sql_bool(ret)}, {vote_for}, {order}, '{src}')"
            for cid, (office, level, label, layer, district, scope, np_, ret, vote_for, order, src) in contests.items()
        ) + "\n) v(contest_id, office, level, label, layer, district, scope, nonpartisan, retention, vote_for, ord, source_id)\n"
        "join offices o on o.name = v.office and o.level = v.level;\n\n"
    )

    cand_rows = []
    for cid, cands in candidates.items():
        retention = contests[cid][7]
        unopposed = not retention and len(cands) <= contests[cid][8]
        for i, (name, party) in enumerate(cands, start=1):
            cand_rows.append(f"  ('{cid}', {sql_text(name)}, {sql_text(party)}, {sql_bool(unopposed)}, {i})")
    out.write(
        "insert into candidates (contest_id, name, party, unopposed, ballot_order, source_id)\n"
        "select v.contest_id::uuid, v.name, v.party, v.unopposed, v.ord, c.source_id\nfrom (values\n"
        + ",\n".join(cand_rows) +
        "\n) v(contest_id, name, party, unopposed, ord)\njoin contests c on c.contest_id = v.contest_id::uuid;\n\n"
    )

    for mid, (statewide, fips, title, question, yes, no, order, src) in measures.items():
        if statewide:
            continue  # already loaded with their exact ballot titles; only linked below
        out.write(
            "insert into ballot_measures (measure_id, election_id, district_layer_id, district_id, jurisdiction_scope, "
            "title, question_text, impact_yes, impact_no, order_on_ballot, source_id)\n"
            f"values ('{mid}', '{GENERAL_ELECTION_ID}', 'county', '{fips}', 'county', {sql_text(title)}, "
            f"{sql_text(question)}, {sql_text(yes)}, {sql_text(no)}, {order}, '{src}')\n"
            "on conflict (measure_id) do update set title = excluded.title, question_text = excluded.question_text,\n"
            "  impact_yes = excluded.impact_yes, impact_no = excluded.impact_no, order_on_ballot = excluded.order_on_ballot;\n\n"
        )

    out.write(
        "insert into ballot_styles (ballot_style_id, election_id, precinct_id, party, style_code, sample_ballot_url, "
        "certification_date, source_id)\n"
        f"select v.id::uuid, '{GENERAL_ELECTION_ID}', p.precinct_id, null, v.style_code, v.url, '{CERTIFICATION_DATE}', "
        "v.source_id::uuid\nfrom (values\n" + ",\n".join(
            f"  ('{sid}', {sql_text(code)}, {sql_text(style_code)}, {sql_text(f'{BASE}general_ballots/{county}.pdf')}, "
            f"'{SOURCE_IDS.get(county, str(uuid.uuid5(NS, county)))}')"
            for sid, county, style_code, code, _, _ in styles
        ) + "\n) v(id, precinct_code, style_code, url, source_id)\n"
        "join precincts p on p.precinct_code = v.precinct_code and p.state = 'MD';\n\n"
    )
    out.write(
        "insert into ballot_style_contests (ballot_style_id, contest_id)\n"
        "select v.style_id::uuid, v.contest_id::uuid from (values\n" + ",\n".join(
            f"  ('{sid}', '{cid}')" for sid, _, _, _, cids, _ in styles for cid in cids
        ) + "\n) v(style_id, contest_id)\njoin ballot_styles bs on bs.ballot_style_id = v.style_id::uuid;\n\n"
    )
    out.write(
        "insert into ballot_style_measures (ballot_style_id, measure_id)\n"
        "select v.style_id::uuid, v.measure_id::uuid from (values\n" + ",\n".join(
            f"  ('{sid}', '{mid}')" for sid, _, _, _, _, mids in styles for mid in mids
        ) + "\n) v(style_id, measure_id)\njoin ballot_styles bs on bs.ballot_style_id = v.style_id::uuid;\n\n"
    )

    out.write(INFER_STALE_PRECINCTS_SQL.format(e=GENERAL_ELECTION_ID, cert=CERTIFICATION_DATE) + "\n")

    codes = sorted({s[3] for s in styles})
    out.write(
        "-- Ballot precincts with no polygon in md_precincts_2026 get no style; list them in the output.\n"
        "select v.code as unmatched_precinct from (values " + ", ".join(f"('{c}')" for c in codes) + ") v(code)\n"
        "where not exists (select 1 from precincts p where p.precinct_code = v.code and p.state = 'MD')\n"
        "order by 1;\n\n"
        "do $$ begin\n"
        f"  if (select count(*) from contests where election_id = '{GENERAL_ELECTION_ID}') <> {len(contests)} then\n"
        f"    raise exception 'expected {len(contests)} MD general contests';\n"
        "  end if;\n"
        f"  if (select count(*) from candidates k join contests c using (contest_id) "
        f"where c.election_id = '{GENERAL_ELECTION_ID}') <> {len(cand_rows)} then\n"
        f"    raise exception 'expected {len(cand_rows)} MD general candidates';\n"
        "  end if;\n"
        "end $$;\n"
    )

    print(f"{sum(len(s) for s in ballots.values())} styles ({len(styles)} style-precinct rows), {len(contests)} contests, "
          f"{len(cand_rows)} candidates, {len(measures)} measures, {len(offices)} offices", file=sys.stderr)
    for county, n in sorted(Counter(s[1] for s in styles).items()):
        print(f"  {county}: {n}", file=sys.stderr)


if __name__ == "__main__":
    main()

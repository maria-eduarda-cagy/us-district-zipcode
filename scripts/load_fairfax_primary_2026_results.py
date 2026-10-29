"""Loads the 2026 Virginia party primaries (held 2026-08-04) as they applied to
Fairfax County, with official results, from Virginia ELECT's results site
(https://enr.elections.virginia.gov/results/public/virginia/elections/
2026-August-Republican-Primary and ...-Democratic-Primary, marked "OFFICIAL
RESULTS").

Only three primaries touched Fairfax County voters:
  - Republican, U.S. Senate (statewide)
  - Republican, House of Representatives 10th District
  - Democratic, House of Representatives 8th District
The Democratic Senate primary was cancelled (Warner unopposed) and neither
party held an 11th District primary, so 11th CD precincts (e.g. Herndon) only
had the Republican Senate primary. Herndon's town offices are nonpartisan and
have no primary.

Precinct -> ballot style follows the general loader's congressional district
assignment (same 2021 map; the redistricting referendum was voided before the
primary). Virginia primaries are open, so a precinct gets one style per party
that held a primary there. Pioneer (409) is split 11/8: it gets both
Republican styles and, for the Democratic primary, the 8th CD style plus an
empty 11th CD style, so sample-ballot's style selection doesn't show the 8th
District primary to an address in the 11th CD part of the precinct.

Totals are jurisdiction-wide (statewide / whole congressional district), summed
over every precinct row of the official "Election Results" CSV. Fails loudly
(exit 1, no SQL) if the CSV's candidates for a contest differ from CONTESTS,
or if the computed winner differs from the official "Election Winners" CSV.

Usage:
    python3 scripts/load_fairfax_primary_2026_results.py > out.sql
"""
import csv
import io
import json
import os
import sys
import urllib.parse
import urllib.request
import uuid
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import load_fairfax_general_2026 as general  # noqa: E402

ENR = "https://enr.elections.virginia.gov"
JURISDICTION_ID = "d2c804ee-4ec2-46bb-91d7-5b41526eab03"  # "virginia" on the ENR site
NS = uuid.uuid5(uuid.NAMESPACE_URL, ENR + "/results/public/virginia/elections/2026-August-Primary")
ELECTION_ID = str(uuid.uuid5(NS, "election"))
COUNTY_FIPS = general.COUNTY_FIPS

DEM = "Democratic"
REP = "Republican"
ELECTIONS = {
    REP: "2026-August-Republican-Primary",
    DEM: "2026-August-Democratic-Primary",
}

# key -> (party, OfficeTitle in the CSV, office_name, office_level, contest_label,
#         district_layer_id, district_id, scope, order, reporting_unit, candidates)
CONTESTS = {
    "senate_r": (REP, "Member, United States Senate", "U.S. Senator", "Federal", "Member United States Senate",
                 None, None, "at_large", 1, "Virginia", [
                     "Bert Mizusawa",
                     "David E. Williams",
                     "Kim Farington",
                 ]),
    "house10_r": (REP, "Member, House of Representatives (10th District)", "U.S. Representative", "Federal",
                  "Member House of Representatives 10th District", "cd119", "5110", "district", 2,
                  "Congressional District 10", [
                      "Dave T. Beckwith",
                      "Julie Anna Perry",
                      "Anthony L. Suttles",
                      "M. Sam Wong",
                  ]),
    "house8_d": (DEM, "Member, House of Representatives (8th District)", "U.S. Representative", "Federal",
                 "Member House of Representatives 8th District", "cd119", "5108", "district", 2,
                 "Congressional District 8", [
                     "Donald S. Beyer, Jr.",
                     "Mo Seifeldein",
                     "Adam M. Dunigan",
                     "Michael Christian Duffin",
                     "Lorena Thorne Bruner",
                 ]),
}

# style_code -> (party, contest keys)
STYLES = {
    "Republican Primary 8th CD": (REP, ["senate_r"]),
    "Republican Primary 10th CD": (REP, ["senate_r", "house10_r"]),
    "Republican Primary 11th CD": (REP, ["senate_r"]),
    "Democratic Primary 8th CD": (DEM, ["house8_d"]),
    "Democratic Primary 11th CD": (DEM, []),  # Pioneer (409) only; see docstring
}


def precinct_styles():
    styles = {}
    for cd, numbers in general.PRECINCTS_BY_CD.items():
        for n in numbers:
            styles[n] = [f"Republican Primary {cd}th CD"] + (["Democratic Primary 8th CD"] if cd == "8" else [])
    assert "409" not in styles
    styles["409"] = [
        "Republican Primary 8th CD", "Republican Primary 11th CD",
        "Democratic Primary 8th CD", "Democratic Primary 11th CD",
    ]
    assert len(styles) == general.EXPECTED_PRECINCTS, len(styles)
    return styles


def dq(value: str, tag: str = "q") -> str:
    return f"${tag}${value}${tag}$"


def sql_text(value):
    return "null" if value is None else dq(str(value))


def sql_bool(value: bool) -> str:
    return "true" if value else "false"


def fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "us-district-zipcode-loader/1.0"})
    with urllib.request.urlopen(req, timeout=120) as resp:
        return resp.read()


def fetch_reports(slug: str):
    """Official results + winners CSVs for one party primary, located through the
    ENR API (blob names carry a GUID that changes when the state republishes)."""
    election = json.loads(fetch(f"{ENR}/results/public/api/elections/virginia/{slug}"))
    if not election.get("isOfficialResults"):
        raise SystemExit(f"ERROR: {slug} results are not marked official")
    blobs = {
        r["reportName"]: r["blobName"]
        for cat in election["publicReportCategories"] for r in cat["reports"]
    }
    urls = {
        name: f"{ENR}/cdn/results/{JURISDICTION_ID}/{urllib.parse.quote(blobs[name])}"
        for name in ("Election Results", "Election Winners")
    }
    rows = {
        name: list(csv.DictReader(io.StringIO(fetch(url).decode("utf-8-sig"))))
        for name, url in urls.items()
    }
    return urls["Election Results"], election["lastUpdated"][:10], rows["Election Results"], rows["Election Winners"]


def main():
    reports = {party: fetch_reports(slug) for party, slug in ELECTIONS.items()}
    for party, (url, last_updated, rows, _) in reports.items():
        print(f"Fetched {party} primary results: {len(rows)} rows (last updated {last_updated})", file=sys.stderr)

    errors = []
    totals = {}  # contest key -> Counter(candidate -> votes)
    winners = {}
    for key, (party, office_title, *_, candidates) in CONTESTS.items():
        _, _, rows, winner_rows = reports[party]
        votes = Counter()
        for r in rows:
            if r["OfficeTitle"] == office_title:
                if r["WriteInVote"] != "0":
                    errors.append(f"{key}: unexpected write-in row {r['CandidateName']}")
                votes[r["CandidateName"]] += int(r["TOTAL_VOTES"])
        if set(votes) != set(candidates):
            errors.append(
                f"{key}: only in results {sorted(set(votes) - set(candidates))}, "
                f"only in CONTESTS {sorted(set(candidates) - set(votes))}"
            )
        official = {w["BallotName"] for w in winner_rows if w["Office"] == office_title}
        top = {votes.most_common(1)[0][0]} if votes else set()
        if official != top:
            errors.append(f"{key}: official winner {sorted(official)} != top vote-getter {sorted(top)}")
        totals[key] = votes
        winners[key] = official

    if errors:
        for e in errors:
            print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)

    out = sys.stdout
    out.write("-- Generated by scripts/load_fairfax_primary_2026_results.py. Idempotent: safe to re-run.\n\n")

    source_ids = {}
    for party, (url, last_updated, _, _) in reports.items():
        source_ids[party] = str(uuid.uuid5(NS, url))
        out.write(
            "insert into sources (source_id, source_url, source_type, effective_date, confidence, notes)\n"
            f"values ('{source_ids[party]}', {sql_text(url)}, 'election_results_csv', '{last_updated}', 1.0, "
            f"{sql_text(f'Virginia ELECT official 2026 August {party} primary results; effective_date = lastUpdated')})\n"
            "on conflict (source_id) do update set fetched_at = now(), effective_date = excluded.effective_date;\n\n"
        )

    out.write(
        "insert into elections (election_id, name, election_type, election_date, state, jurisdiction_scope, "
        "party_scope, is_special, status, source_id)\n"
        f"values ('{ELECTION_ID}', '2026 Primary Election', 'primary', '2026-08-04', 'VA', 'state', null, false, "
        f"'certified', '{source_ids[REP]}')\n"
        "on conflict (election_id) do update set name = excluded.name, status = excluded.status;\n\n"
    )

    for key, (party, _, office_name, level, label, layer_id, district_id, scope, order, reporting_unit,
              candidates) in CONTESTS.items():
        out.write(
            "insert into offices (name, level, description)\n"
            f"values ({sql_text(office_name)}, {sql_text(level)}, {sql_text(office_name)})\n"
            "on conflict (name, level) do nothing;\n\n"
        )
        out.write(
            "insert into contests (election_id, office_id, district_layer_id, district_id, contest_label, "
            "scope, nonpartisan, retention, write_in_allowed, vote_for, order_on_ballot, source_id)\n"
            f"select '{ELECTION_ID}', o.office_id, {sql_text(layer_id)}, {sql_text(district_id)}, {sql_text(label)}, "
            f"{sql_text(scope)}, false, false, false, 1, {order}, '{source_ids[party]}'\n"
            f"from offices o where o.name = {sql_text(office_name)} and o.level = {sql_text(level)}\n"
            "on conflict (election_id, office_id, coalesce(district_id, ''), contest_label) do update\n"
            "  set scope = excluded.scope, order_on_ballot = excluded.order_on_ballot;\n\n"
        )
        for i, cand_name in enumerate(candidates, start=1):
            out.write(
                "insert into candidates (contest_id, name, party, unopposed, ballot_order, source_id)\n"
                f"select c.contest_id, {sql_text(cand_name)}, {sql_text(party)}, false, {i}, c.source_id\n"
                "from contests c\n"
                f"where c.election_id = '{ELECTION_ID}' and c.contest_label = {sql_text(label)}\n"
                "and not exists (\n"
                "  select 1 from candidates existing\n"
                f"  where existing.contest_id = c.contest_id and existing.name = {sql_text(cand_name)}\n"
                ");\n\n"
            )
            out.write(
                "insert into contest_results (contest_id, candidate_id, primary_party, reporting_unit, votes, "
                "is_winner, source_id)\n"
                f"select c.contest_id, cd.candidate_id, {sql_text(party)}, {sql_text(reporting_unit)}, "
                f"{totals[key][cand_name]}, {sql_bool(cand_name in winners[key])}, '{source_ids[party]}'\n"
                "from contests c join candidates cd on cd.contest_id = c.contest_id\n"
                f"where c.election_id = '{ELECTION_ID}' and c.contest_label = {sql_text(label)} "
                f"and cd.name = {sql_text(cand_name)}\n"
                "on conflict (candidate_id, coalesce(primary_party, '')) do update\n"
                "  set votes = excluded.votes, is_winner = excluded.is_winner,\n"
                "      reporting_unit = excluded.reporting_unit, source_id = excluded.source_id;\n\n"
            )

    rows = ",\n".join(
        f"  ('{COUNTY_FIPS}-{n}', {sql_text(style)}, {sql_text(STYLES[style][0])})"
        for n, styles in sorted(precinct_styles().items()) for style in styles
    )
    out.write(
        "insert into ballot_styles (election_id, precinct_id, party, style_code, sample_ballot_url, source_id)\n"
        f"select '{ELECTION_ID}', p.precinct_id, v.party, v.style_code, null,\n"
        f"  case v.party when '{REP}' then '{source_ids[REP]}'::uuid else '{source_ids[DEM]}'::uuid end\n"
        f"from (values\n{rows}\n) v(precinct_code, style_code, party)\n"
        f"join precincts p on p.precinct_code = v.precinct_code and p.state = 'VA' and p.county_fips = '{COUNTY_FIPS}'\n"
        "on conflict (election_id, precinct_id, style_code) do update\n"
        "  set party = excluded.party, source_id = excluded.source_id;\n\n"
    )

    links = ",\n".join(
        f"  ({sql_text(style)}, {sql_text(CONTESTS[key][4])})" for style, (_, keys) in STYLES.items() for key in keys
    )
    out.write(
        "insert into ballot_style_contests (ballot_style_id, contest_id)\n"
        "select bs.ballot_style_id, c.contest_id\n"
        f"from (values\n{links}\n) v(style_code, contest_label)\n"
        f"join ballot_styles bs on bs.election_id = '{ELECTION_ID}' and bs.style_code = v.style_code\n"
        f"join contests c on c.election_id = '{ELECTION_ID}' and c.contest_label = v.contest_label\n"
        "on conflict (ballot_style_id, contest_id) do nothing;\n\n"
    )

    expected_styles = sum(len(s) for s in precinct_styles().values())
    expected_results = sum(len(c[-1]) for c in CONTESTS.values())
    out.write(
        "do $check$ begin\n"
        f"  if (select count(*) from ballot_styles where election_id = '{ELECTION_ID}') <> {expected_styles} then\n"
        f"    raise exception 'expected {expected_styles} Fairfax primary ballot styles: a precinct code did not match';\n"
        "  end if;\n"
        "  if (select count(*) from contest_results r join contests c using (contest_id)\n"
        f"      where c.election_id = '{ELECTION_ID}') <> {expected_results} then\n"
        f"    raise exception 'expected {expected_results} primary contest_results rows';\n"
        "  end if;\n"
        "end $check$;\n"
    )

    print(f"Done: {expected_styles} ballot styles, {expected_results} candidate results.", file=sys.stderr)


if __name__ == "__main__":
    main()

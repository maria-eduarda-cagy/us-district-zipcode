"""ETL: pulls the official 2026 MD primary results (MSBE results CSVs, from
https://elections.maryland.gov/elections/2026/election_data/index.html) for
every contest on precinct 008-006's two primary ballots (BS DEM 125 / BS REP
125) and generates SQL loading them into contest_results.

Totals are for each contest's whole jurisdiction -- the number that decides
who won -- not just the precinct:
  - statewide offices: sum of the "State of Maryland" row across all
    congressional districts in GP26_CongressionalBreakDown*.csv (this sum
    matches the per-precinct file exactly; checked 2026-10-20)
  - Congressional District 8: same breakdown file. NOT the Montgomery County
    file: CD 8 has a sliver in Prince George's (3 Raskin votes)
  - Legislative District 14: GP26_LegislativeBreakDown*.csv
  - county offices: GP26_16*Results.csv (Montgomery = county code 16)
  - Council District 7 / Board of Education District 3:
    GP26_16Counc*Results.csv, summed across council districts

Fails loudly (exit 1, no SQL) if any candidate in the results file doesn't
match a candidate loaded by the primary ballot loaders, or vice versa --
a silent name mismatch would drop a candidate's result.

Usage:
    python3 scripts/load_montgomery_primary_2026_results.py > out.sql
"""
import csv
import io
import os
import sys
import urllib.request
import uuid
from email.utils import parsedate_to_datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import load_montgomery_primary_2026_bs_dem_125 as dem_ballot  # noqa: E402
import load_montgomery_primary_2026_bs_rep_125 as rep_ballot  # noqa: E402

BASE_URL = "https://elections.maryland.gov/elections/2026/election_data/"
PRIMARY_ELECTION_ID = "22222222-2222-2222-2222-222222222222"

DEM = "Democratic"
REP = "Republican"
STATE = "State of Maryland"
COUNTY = "Montgomery County"
LD14 = "Legislative District 14"

CB_DEM = "GP26_CongressionalBreakDownDemocratic.csv"
CB_REP = "GP26_CongressionalBreakDownRepublican.csv"
LB_DEM = "GP26_LegislativeBreakDownDemocratic.csv"
MC_DEM = "GP26_16DemocraticResults.csv"
MC_REP = "GP26_16RepublicanResults.csv"
MC_NON = "GP26_16Non-PartisanResults.csv"
MC_COUNC_DEM = "GP26_16CouncDemocraticResults.csv"
MC_COUNC_REP = "GP26_16CouncRepublicanResults.csv"
MC_COUNC_NON = "GP26_16CouncNon-PartisanResults.csv"

# (contest_label in our DB, primary_party (None = nonpartisan), results file, "Office Name", "Office District", reporting_unit)
RESULTS = [
    ("Governor / Lieutenant Governor", DEM, CB_DEM, "Governor / Lt. Governor", "", STATE),
    ("Comptroller", DEM, CB_DEM, "Comptroller", "", STATE),
    ("Attorney General", DEM, CB_DEM, "Attorney General", "", STATE),
    ("Representative in Congress District 8", DEM, CB_DEM, "U.S. Congress", "08", "Congressional District 8"),
    ("State Senator District 14", DEM, LB_DEM, "State Senator", "14", LD14),
    ("House of Delegates District 14", DEM, LB_DEM, "House of Delegates", "14", LD14),
    ("County Executive", DEM, MC_DEM, "County Executive", "", COUNTY),
    ("County Council At-Large", DEM, MC_DEM, "County Council At Large", "", COUNTY),
    ("County Council District 7", DEM, MC_COUNC_DEM, "County Council", "007", "Council District 7"),
    ("Judge of the Circuit Court Circuit 6", DEM, MC_DEM, "Judge Circuit Court", "Montgomery County Circuit Court 06", COUNTY),
    ("State's Attorney", DEM, MC_DEM, "State's Attorney", "", COUNTY),
    ("Clerk of the Circuit Court", DEM, MC_DEM, "Clerk Circuit Court", "", COUNTY),
    ("Register of Wills", DEM, MC_DEM, "Register of Wills", "", COUNTY),
    ("Sheriff", DEM, MC_DEM, "Sheriff", "", COUNTY),
    ("Democratic Central Committee At-Large", DEM, MC_DEM, "DEM Cent Comm at Large", "", COUNTY),
    ("Democratic Central Committee District 14", DEM, MC_DEM, "DEM Cent Comm", "14", LD14),
    ("Governor / Lieutenant Governor", REP, CB_REP, "Governor / Lt. Governor", "", STATE),
    ("Comptroller", REP, CB_REP, "Comptroller", "", STATE),
    ("Attorney General", REP, CB_REP, "Attorney General", "", STATE),
    ("Representative in Congress District 8", REP, CB_REP, "U.S. Congress", "08", "Congressional District 8"),
    ("County Executive", REP, MC_REP, "County Executive", "", COUNTY),
    ("County Council At-Large", REP, MC_REP, "County Council At Large", "", COUNTY),
    ("County Council District 7", REP, MC_COUNC_REP, "County Council", "007", "Council District 7"),
    ("Judge of the Circuit Court Circuit 6", REP, MC_REP, "Judge Circuit Court", "Montgomery County Circuit Court 06", COUNTY),
    ("Register of Wills", REP, MC_REP, "Register of Wills", "", COUNTY),
    ("Republican Central Committee At-Large", REP, MC_REP, "REP Cent Comm at Large", "", COUNTY),
    ("Republican Central Committee District 14", REP, MC_REP, "REP Cent Committee", "14", LD14),
    # Board of Education district members are elected countywide (residency districts).
    ("Board of Education At-Large", None, MC_NON, "Board of Ed at Large", "", COUNTY),
    ("Board of Education District 3", None, MC_COUNC_NON, "Board of Education", "003", COUNTY),
]

BREAKDOWN_COLUMN_PREFIXES = ("Congressional District", "Legislative District", "Councilmanic District")


def dq(value: str, tag: str = "q") -> str:
    return f"${tag}${value}${tag}$"


def sql_text(value):
    return "null" if value is None else dq(str(value))


def sql_bool(value: bool) -> str:
    return "true" if value else "false"


def source_id_for(file_name: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, BASE_URL + file_name))


def fetch_csv(file_name: str):
    # elections.maryland.gov answers 403 to urllib's default User-Agent.
    req = urllib.request.Request(BASE_URL + file_name, headers={"User-Agent": "us-district-zipcode-loader/1.0"})
    with urllib.request.urlopen(req, timeout=120) as resp:
        last_modified = parsedate_to_datetime(resp.headers["Last-Modified"]).date().isoformat()
        text = resp.read().decode("utf-8-sig")
    # Headers and values carry stray trailing spaces ("Total Votes ").
    rows = [
        {(k or "").strip(): (v or "").strip() for k, v in row.items()}
        for row in csv.DictReader(io.StringIO(text))
    ]
    return rows, last_modified


def row_votes(row) -> int:
    if "Total Votes" in row:
        return int(row["Total Votes"])
    return sum(int(v) for k, v in row.items() if k.startswith(BREAKDOWN_COLUMN_PREFIXES) and v)


def normalize_name(name: str) -> str:
    # Tickets are "A and B" in the results files, "A / B" on the ballot.
    return name.replace(" and ", " / ")


def expected_candidates():
    """(contest_label, primary_party) -> candidate names, from the primary ballot loaders."""
    expected = {}
    for _, _, label, _, _, _, nonpartisan, _, _, candidates in dem_ballot.CONTESTS:
        expected[(label, None if nonpartisan else DEM)] = {name for name, _ in candidates}
    for _, _, label, _, _, _, nonpartisan, _, _, candidates in rep_ballot.CONTESTS:
        if nonpartisan:
            continue  # same nonpartisan contest as on the Democratic ballot
        names = {name for name, _ in candidates}
        if label == "Judge of the Circuit Court Circuit 6":
            names = set(rep_ballot.CROSS_FILED_JUDGES)
        expected[(label, REP)] = names
    return expected


def main():
    files = {}
    for file_name in sorted({spec[2] for spec in RESULTS}):
        files[file_name] = fetch_csv(file_name)
        print(f"Fetched {file_name} (Last-Modified {files[file_name][1]})", file=sys.stderr)

    expected = expected_candidates()
    missing_specs = set(expected) - {(label, party) for label, party, *_ in RESULTS}
    errors = [f"No results mapping for {key}" for key in sorted(missing_specs, key=str)]

    results = []  # (label, party, candidate_name, votes, is_winner, reporting_unit, file_name)
    for label, party, file_name, office_name, office_district, reporting_unit in RESULTS:
        rows, _ = files[file_name]
        matched = [
            r for r in rows
            if r["Office Name"] == office_name and r["Office District"] == office_district
            and r.get("County", "00") == "00"  # breakdown files: statewide row only
        ]
        got = {normalize_name(r["Candidate Name"]): r for r in matched}
        want = expected.get((label, party), set())
        if set(got) != want:
            errors.append(
                f"{label} [{party}] in {file_name}: only in results {sorted(set(got) - want)}, "
                f"only in ballot {sorted(want - set(got))}"
            )
            continue
        for name, r in got.items():
            results.append((label, party, name, row_votes(r), r["Winner"] == "Y", reporting_unit, file_name))

    if errors:
        for e in errors:
            print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)

    out = sys.stdout
    out.write("-- Generated by scripts/load_montgomery_primary_2026_results.py. Idempotent: safe to re-run.\n\n")

    for file_name, (_, last_modified) in sorted(files.items()):
        out.write(
            "insert into sources (source_id, source_url, source_type, effective_date, confidence, notes)\n"
            f"values ('{source_id_for(file_name)}', {sql_text(BASE_URL + file_name)}, "
            f"{sql_text('election_results_csv')}, '{last_modified}', 1.0, "
            f"{sql_text('MSBE official 2026 primary results; effective_date = file Last-Modified')})\n"
            "on conflict (source_id) do update set fetched_at = now(), effective_date = excluded.effective_date;\n\n"
        )

    for label, party, name, votes, is_winner, reporting_unit, file_name in results:
        out.write(
            "insert into contest_results (contest_id, candidate_id, primary_party, reporting_unit, votes, "
            "is_winner, source_id)\n"
            f"select c.contest_id, cd.candidate_id, {sql_text(party)}, {sql_text(reporting_unit)}, {votes}, "
            f"{sql_bool(is_winner)}, '{source_id_for(file_name)}'\n"
            "from contests c join candidates cd on cd.contest_id = c.contest_id\n"
            f"where c.election_id = '{PRIMARY_ELECTION_ID}' and c.contest_label = {sql_text(label)} "
            f"and cd.name = {sql_text(name)}\n"
            "on conflict (candidate_id, coalesce(primary_party, '')) do update\n"
            "  set votes = excluded.votes, is_winner = excluded.is_winner,\n"
            "      reporting_unit = excluded.reporting_unit, source_id = excluded.source_id;\n\n"
        )

    # insert ... select silently inserts nothing if a contest/candidate row is
    # missing in the DB; make that a hard failure instead.
    out.write(
        "do $check$ begin\n"
        "  if (select count(*) from contest_results r join contests c using (contest_id)\n"
        f"      where c.election_id = '{PRIMARY_ELECTION_ID}') <> {len(results)} then\n"
        f"    raise exception 'expected {len(results)} primary contest_results rows';\n"
        "  end if;\n"
        "end $check$;\n"
    )

    print(f"Done: {len(results)} candidate results.", file=sys.stderr)


if __name__ == "__main__":
    main()

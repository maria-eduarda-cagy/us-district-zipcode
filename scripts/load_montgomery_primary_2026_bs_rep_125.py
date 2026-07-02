"""Loads the real, certified Republican primary ballot (BS REP 125) that
applies to Montgomery County precinct 008-006 (Ashton, MD -- same precinct
as scripts/load_montgomery_primary_2026_bs_dem_125.py). Transcribed from the
official certified ballot PDF published by the Maryland State Board of
Elections: https://elections.maryland.gov/elections/2026/primary_ballots/
Montgomery.pdf (certified 2026-04-14, election held 2026-06-23), pages
763-764.

All 13 contests on this ballot style are included. Cross-checked against a
third-party structured extraction (Montgomery_primary_election_friendly.json)
and independently re-verified word-by-word with `pdftohtml -xml` (which
preserves per-word top/left coordinates) directly against the certified PDF
-- because that same friendly.json had a confirmed data bug elsewhere (see
docs/mvp-scope.md), every name, ticket, and "vote for N" rule below was
cross-checked against the raw PDF coordinates, not trusted blindly. Zero
discrepancies found for this precinct's Republican ballot.

Contests that also exist on the Democratic ballot (same office_name +
contest_label + district_id) intentionally reuse the SAME order_on_ballot
values as scripts/load_montgomery_primary_2026_bs_dem_125.py, because the
contests UPSERT overwrites vote_for/scope/nonpartisan/order_on_ballot on
conflict -- using mismatched values here would silently corrupt the
already-loaded Democratic data.

"Nomination Vacant" / "Nomination Vacant /Nominacion Vacante" placeholder
entries (seats nobody filed for) are omitted entirely -- they are not real
candidates.

Judge of the Circuit Court Circuit 6 and both Board of Education contests
carry NO new candidates here: the exact same 5 judges appear on both
party ballots (Maryland judicial cross-filing) and Board of Education is
already nonpartisan and shared. Only the ballot_style_contests link is
added for these, so the contest correctly shows as "on this ballot" too.
The Judge of the Circuit Court candidates' party is corrected separately
(see the UPDATE statement below) from 'Democratic' to 'Cross-filed', since
tagging cross-filed judges as exclusively Democratic misrepresents them.

Usage:
    python3 scripts/load_montgomery_primary_2026_bs_rep_125.py > out.sql
"""
import sys

SOURCE_URL = "https://elections.maryland.gov/elections/2026/primary_ballots/Montgomery.pdf"
PRECINCT_CODE = "2403108-006"  # Ashton, Montgomery County (VTD from md_precincts_2026 layer)
BALLOT_STYLE_CODE = "BS REP 125"
SOURCE_ID = "11111111-1111-1111-1111-111111111111"  # same certified PDF as the Democratic loader
ELECTION_ID = "22222222-2222-2222-2222-222222222222"  # same primary election, party_scope=null
BALLOT_STYLE_ID = "77777777-7777-7777-7777-777777777777"  # new; 66666666 is already the early-voting source_id

CROSS_FILED_JUDGES = [
    "Sharon V. Burrell",
    "Victor M. Del Pino",
    "James J. Dietrich",
    "Catherine H. McQueen",
    "Marylin Pierre",
]

# (office_name, office_level, contest_label, district_layer_id, district_id, scope, nonpartisan, vote_for, order, [(name, unopposed), ...])
CONTESTS = [
    ("Governor / Lieutenant Governor", "State", "Governor / Lieutenant Governor", None, None, "at_large", False, 1, 1, [
        ("Carl A. Brunner, Jr. / Kevin L. Rhodes, Sr.", False),
        ("L. D. Burkindine / Jeremy M. Shifflett", False),
        ("Dan Cox / Rob Krop", False),
        ("Ed Hale / Tyrone Keys, Jr.", False),
        ("Douglas Larcomb / Martina D. Duncan", False),
        ("John A. Myrick / Brenda J. Thiam", False),
        ("Michael Oakes / Ronald W. Abend", False),
        ('Nancy Jane Taylor / Rachel Hannah "Mohawk" Swift', False),
        ("Shannon Wright / Reba A. Hawkins", False),
    ]),
    ("Comptroller", "State", "Comptroller", None, None, "at_large", False, 1, 2, [
        ("Sonya Dunn", True),
    ]),
    ("Attorney General", "State", "Attorney General", None, None, "at_large", False, 1, 3, [
        ("James B. Rutledge, III", True),
    ]),
    ("U.S. Representative", "Federal", "Representative in Congress District 8", "cd119", "2408", "district", False, 1, 4, [
        ("Anita Mpambara Cox", False),
        ("Donald L. Lech", False),
        ("Cheryl Riley", False),
        ("Michael Yadeta", False),
    ]),
    ("County Executive", "Local", "County Executive", "county", "24031", "at_large", False, 1, 7, [
        ("Shelly Skolnick", False),
        ("Esther Wells", False),
    ]),
    # 3x "Nomination Vacant" placeholders excluded -- not real candidates.
    ("County Council", "Local", "County Council At-Large", "county", "24031", "at_large", False, 4, 8, [
        ("Sherwin Wells", True),
    ]),
    ("County Council", "Local", "County Council District 7", None, None, "district", False, 1, 9, [
        ("Harold Maldonado", True),
    ]),
    # No new candidates: same 5 cross-filed judges already loaded by the Democratic script.
    ("Judge of the Circuit Court", "Local", "Judge of the Circuit Court Circuit 6", None, None, "at_large", False, 4, 10, []),
    ("Register of Wills", "Local", "Register of Wills", "county", "24031", "at_large", False, 1, 13, [
        ("T. Dolores Reyes", True),
    ]),
    ("Republican Central Committee", "Local", "Republican Central Committee At-Large", "county", "24031", "at_large", False, 4, 19, [
        ("Marcus Alzona", True),
        ("Dan Cuda", True),
        ("Gregory Decker", True),
        ('Reardon "Sully" Sullivan', True),
    ]),
    # 1x "Nomination Vacant /Nominacion Vacante" placeholder excluded.
    ("Republican Central Committee", "Local", "Republican Central Committee District 14", "sldu", "24014", "district", False, 2, 20, [
        ("Josephine Salazar", True),
    ]),
    # No new candidates: same nonpartisan candidates already loaded by the Democratic script.
    ("Board of Education", "Local", "Board of Education At-Large", "county", "24031", "at_large", True, 1, 17, []),
    ("Board of Education", "Local", "Board of Education District 3", None, None, "district", True, 1, 18, []),
]


def dq(value: str, tag: str = "q") -> str:
    return f"${tag}${value}${tag}$"


def sql_text(value):
    return "null" if value is None else dq(str(value))


def sql_bool(value: bool) -> str:
    return "true" if value else "false"


def main():
    out = sys.stdout
    out.write("-- Generated by scripts/load_montgomery_primary_2026_bs_rep_125.py. Idempotent: safe to re-run.\n\n")

    out.write(
        "insert into ballot_styles (ballot_style_id, election_id, precinct_id, party, style_code, "
        "sample_ballot_url, certification_date, source_id)\n"
        f"select '{BALLOT_STYLE_ID}', '{ELECTION_ID}', "
        f"p.precinct_id, {sql_text('Republican')}, {sql_text(BALLOT_STYLE_CODE)}, {sql_text(SOURCE_URL)}, "
        f"'2026-04-14', '{SOURCE_ID}'\n"
        f"from precincts p where p.precinct_code = {sql_text(PRECINCT_CODE)} and p.state = 'MD'\n"
        "on conflict (ballot_style_id) do nothing;\n\n"
    )

    for office_name, level, label, layer_id, district_id, scope, nonpartisan, vote_for, order, candidates in CONTESTS:
        out.write(
            "insert into offices (name, level, description)\n"
            f"values ({sql_text(office_name)}, {sql_text(level)}, {sql_text(office_name)})\n"
            "on conflict (name, level) do nothing;\n\n"
        )

        out.write(
            "insert into contests (election_id, office_id, district_layer_id, district_id, contest_label, "
            "scope, nonpartisan, vote_for, order_on_ballot, source_id)\n"
            f"select '{ELECTION_ID}', o.office_id, "
            f"{sql_text(layer_id)}, {sql_text(district_id)}, {sql_text(label)}, {sql_text(scope)}, "
            f"{sql_bool(nonpartisan)}, {vote_for}, {order}, "
            f"'{SOURCE_ID}'\n"
            f"from offices o where o.name = {sql_text(office_name)} and o.level = {sql_text(level)}\n"
            "on conflict (election_id, office_id, coalesce(district_id, ''), contest_label) do update\n"
            "  set vote_for = excluded.vote_for, scope = excluded.scope, nonpartisan = excluded.nonpartisan;\n\n"
        )

        candidate_party = None if nonpartisan else "Republican"
        for i, (cand_name, unopposed) in enumerate(candidates, start=1):
            out.write(
                "insert into candidates (contest_id, name, party, unopposed, ballot_order, source_id)\n"
                "select c.contest_id, "
                f"{sql_text(cand_name)}, {sql_text(candidate_party)}, {sql_bool(unopposed)}, {i}, "
                f"'{SOURCE_ID}'\n"
                "from contests c\n"
                f"where c.election_id = '{ELECTION_ID}' and c.contest_label = {sql_text(label)}\n"
                "and not exists (\n"
                "  select 1 from candidates existing\n"
                "  where existing.contest_id = c.contest_id and existing.name = "
                f"{sql_text(cand_name)}\n"
                ");\n\n"
            )

        out.write(
            "insert into ballot_style_contests (ballot_style_id, contest_id)\n"
            f"select '{BALLOT_STYLE_ID}', c.contest_id\n"
            "from contests c\n"
            f"where c.election_id = '{ELECTION_ID}' and c.contest_label = {sql_text(label)}\n"
            "on conflict (ballot_style_id, contest_id) do nothing;\n\n"
        )

    out.write(
        "-- Cross-filing correction: these 5 judges appear identically on both the\n"
        "-- Democratic and Republican ballots. They were originally loaded with\n"
        "-- party='Democratic' by the Democratic script; correct that here rather\n"
        "-- than tag them as belonging to one party only.\n"
    )
    judge_names_sql = ", ".join(sql_text(name) for name in CROSS_FILED_JUDGES)
    out.write(
        "update candidates set party = 'Cross-filed'\n"
        f"where name in ({judge_names_sql})\n"
        "and contest_id = (\n"
        f"  select contest_id from contests where election_id = '{ELECTION_ID}'\n"
        "  and contest_label = 'Judge of the Circuit Court Circuit 6'\n"
        ");\n\n"
    )

    print("Done.", file=sys.stderr)


if __name__ == "__main__":
    main()

"""Loads the real, certified Democratic primary ballot (BS DEM 125) that
applies to Montgomery County precinct 008-006 (Ashton, MD -- the address
used to validate this project's pipeline). Transcribed from the official
certified ballot PDF published by the Maryland State Board of Elections:
https://elections.maryland.gov/elections/2026/primary_ballots/Montgomery.pdf
(certified 2026-04-14, election held 2026-06-23).

All 18 contests on this ballot style are included. The Democratic Central
Committee and Board of Education races (back page) were re-extracted with
`pdftohtml -xml`, which preserves per-word (top, left) coordinates -- plain
pdftotext -layout interleaves this page's two columns unreliably. Verified
against a third-party structured extraction (Montgomery_primary_election_
friendly.json) for the 3 contests where that source agreed; Board of
Education District 3 required an independent coordinate-based re-check
because that source had a data bug there (see docs/mvp-scope.md) -- the
candidate list below was confirmed correct for this specific precinct by
tracing (top, left) positions directly, not by trusting that source.

Usage:
    python3 scripts/load_montgomery_primary_2026_bs_dem_125.py > out.sql
"""
import sys

SOURCE_URL = "https://elections.maryland.gov/elections/2026/primary_ballots/Montgomery.pdf"
PRECINCT_CODE = "2403108-006"  # Ashton, Montgomery County (VTD from md_precincts_2026 layer)
BALLOT_STYLE_CODE = "BS DEM 125"

# (office_name, office_level, contest_label, district_layer_id, district_id, scope, nonpartisan, vote_for, order, [(name, unopposed), ...])
# scope is an explicit, authoritative property of the contest -- whether the
# seat is elected at-large or by sub-district -- and must NOT be inferred
# from whether district_id is set. County Council At-Large is a good example
# of why: it carries district_id='24031' purely to link it to the county's
# boundary/name, but the seat itself is still elected at-large.
# nonpartisan contests (Board of Education) get candidates.party = null, not
# 'Democratic' -- the ballot itself says candidates "may or may not be
# affiliated with any political party", so tagging them Democratic would be
# fabricating an affiliation the source doesn't assert.
CONTESTS = [
    ("Governor / Lieutenant Governor", "State", "Governor / Lieutenant Governor", None, None, "at_large", False, 1, 1, [
        ("Eric S. Felber / LaTrece Hawkins Lytes", False),
        ("Wes Moore / Aruna Miller", False),
    ]),
    ("Comptroller", "State", "Comptroller", None, None, "at_large", False, 1, 2, [
        ("Brooke Elizabeth Lierman", True),
    ]),
    ("Attorney General", "State", "Attorney General", None, None, "at_large", False, 1, 3, [
        ("Anthony G. Brown", True),
    ]),
    ("U.S. Representative", "Federal", "Representative in Congress District 8", "cd119", "2408", "district", False, 1, 4, [
        ("J. D. Kumar", False),
        ("Stephen Alan Leon", False),
        ("Jamie Raskin", False),
        ("Boris Kabel Velasquez", False),
    ]),
    ("State Senator", "State", "State Senator District 14", "sldu", "24014", "district", False, 1, 5, [
        ("Craig J. Zucker", True),
    ]),
    ("House of Delegates", "State", "House of Delegates District 14", "md_delegate_subdistricts_2022", "14", "district", False, 3, 6, [
        ("Alicia Contreras-Donello", False),
        ("Anne R. Kaiser", False),
        ("Bernice Mireku-North", False),
        ("Matt Post", False),
    ]),
    ("County Executive", "Local", "County Executive", "county", "24031", "at_large", False, 1, 7, [
        ("Mithun Banerjee", False),
        ("Andrew Friedson", False),
        ("Evan Glass", False),
        ("Peter James", False),
        ("Will Jawando", False),
    ]),
    ("County Council", "Local", "County Council At-Large", "county", "24031", "at_large", False, 4, 8, [
        ("Fatmata Barrie", False),
        ("Josie Caballero", False),
        ("Radwan Chowdhury", False),
        ("Marc Elrich", False),
        ("Dana Eugene Gassaway", False),
        ("Scott Evan Goldberg", False),
        ("Hamza Khan", False),
        ("Matt Losak", False),
        ("Jim McNulty", False),
        ("Jeremiah Pope", False),
        ("Laurie-Anne Sayles", False),
        ("Prabu Selvam", False),
        ("Karla Silvestre", False),
        ("Steve Solomon", False),
        ("Lelia B. True", False),
        ("Vicki Vergagni", False),
        ("Muhammad Arif Wali", False),
    ]),
    ("County Council", "Local", "County Council District 7", None, None, "district", False, 1, 9, [
        ("Van Free", False),
        ("Sharif Hidayat", False),
        ("Dawn Luedtke", False),
    ]),
    ("Judge of the Circuit Court", "Local", "Judge of the Circuit Court Circuit 6", None, None, "at_large", False, 4, 10, [
        ("Sharon V. Burrell", False),
        ("Victor M. Del Pino", False),
        ("James J. Dietrich", False),
        ("Catherine H. McQueen", False),
        ("Marylin Pierre", False),
    ]),
    ("State's Attorney", "Local", "State's Attorney", "county", "24031", "at_large", False, 1, 11, [
        ("John McCarthy", True),
    ]),
    ("Clerk of the Circuit Court", "Local", "Clerk of the Circuit Court", "county", "24031", "at_large", False, 1, 12, [
        ("Karen Bushell", True),
    ]),
    ("Register of Wills", "Local", "Register of Wills", "county", "24031", "at_large", False, 1, 13, [
        ("Alan S. Bowser", False),
        ("Paul J. Dollahite", False),
        ("Barbara Ebel", False),
    ]),
    ("Sheriff", "Local", "Sheriff", "county", "24031", "at_large", False, 1, 14, [
        ("Will Milam", False),
        ("Maxwell Cornelius Uy", False),
    ]),
    ("Democratic Central Committee", "Local", "Democratic Central Committee At-Large", "county", "24031", "at_large", False, 8, 15, [
        ("Samir Ahmed", False),
        ("Manie Bellot", False),
        ("Deborah S. Belsky", False),
        ("Bill Bien", False),
        ("Sarah Brand-Wiita", False),
        ("Joshua Fischer", False),
        ("Marjorie Goldman", False),
        ("Debra Johnson", False),
        ('Johvet "Jovy" Lopez Ramos', False),
        ("Eric Luedtke", False),
        ("Marko G. Rivera-Oven", False),
        ("Andrew D. Saundry", False),
        ("Rosarie Tucci", False),
        ("Gabrielle Zwi", False),
    ]),
    ("Democratic Central Committee", "Local", "Democratic Central Committee District 14", "sldu", "24014", "district", False, 2, 16, [
        ("Tana Crumbley-Hassan", False),
        ("Arthur Edmunds", False),
        ("Liza Smith", False),
    ]),
    ("Board of Education", "Local", "Board of Education At-Large", "county", "24031", "at_large", True, 1, 17, [
        ("Wylea Chase", False),
        ("Brenda M. Diaz", False),
        ("Omar Lazo", False),
        ("Tiffany E. Wicks", False),
    ]),
    ("Board of Education", "Local", "Board of Education District 3", None, None, "district", True, 1, 18, [
        ("Sharon Creed", False),
        ("Brett DiResta", False),
        ("Andrew Frykman", False),
        ("Sally A. McCarthy", False),
        ('Cassandra "Cassi" Sung', False),
    ]),
]


def dq(value: str, tag: str = "q") -> str:
    return f"${tag}${value}${tag}$"


def sql_text(value):
    return "null" if value is None else dq(str(value))


def sql_bool(value: bool) -> str:
    return "true" if value else "false"


def main():
    out = sys.stdout
    out.write("-- Generated by scripts/load_montgomery_primary_2026_bs_dem_125.py. Idempotent: safe to re-run.\n\n")

    out.write(
        "insert into sources (source_id, source_url, source_type, effective_date, confidence, notes)\n"
        f"values ('11111111-1111-1111-1111-111111111111', {sql_text(SOURCE_URL)}, {sql_text('certified_ballot_pdf')}, "
        "'2026-04-14', 1.0, "
        f"{sql_text('Maryland SBE certified primary ballot, Montgomery County')})\n"
        "on conflict (source_id) do nothing;\n\n"
    )

    out.write(
        "insert into elections (election_id, name, election_type, election_date, state, jurisdiction_scope, "
        "party_scope, is_special, status, source_id)\n"
        "values ('22222222-2222-2222-2222-222222222222', "
        f"{sql_text('2026 Gubernatorial Primary Election')}, 'primary', '2026-06-23', 'MD', 'state', "
        f"{sql_text('Democratic')}, false, 'certified', '11111111-1111-1111-1111-111111111111')\n"
        "on conflict (election_id) do nothing;\n\n"
    )

    out.write(
        "insert into ballot_styles (ballot_style_id, election_id, precinct_id, party, style_code, "
        "sample_ballot_url, certification_date, source_id)\n"
        "select '33333333-3333-3333-3333-333333333333', '22222222-2222-2222-2222-222222222222', "
        f"p.precinct_id, {sql_text('Democratic')}, {sql_text(BALLOT_STYLE_CODE)}, {sql_text(SOURCE_URL)}, "
        "'2026-04-14', '11111111-1111-1111-1111-111111111111'\n"
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
            "select '22222222-2222-2222-2222-222222222222', o.office_id, "
            f"{sql_text(layer_id)}, {sql_text(district_id)}, {sql_text(label)}, {sql_text(scope)}, "
            f"{sql_bool(nonpartisan)}, {vote_for}, {order}, "
            "'11111111-1111-1111-1111-111111111111'\n"
            f"from offices o where o.name = {sql_text(office_name)} and o.level = {sql_text(level)}\n"
            "on conflict (election_id, office_id, coalesce(district_id, ''), contest_label) do update\n"
            "  set vote_for = excluded.vote_for, scope = excluded.scope, nonpartisan = excluded.nonpartisan;\n\n"
        )

        candidate_party = None if nonpartisan else "Democratic"
        for i, (cand_name, unopposed) in enumerate(candidates, start=1):
            out.write(
                "insert into candidates (contest_id, name, party, unopposed, ballot_order, source_id)\n"
                "select c.contest_id, "
                f"{sql_text(cand_name)}, {sql_text(candidate_party)}, {sql_bool(unopposed)}, {i}, "
                "'11111111-1111-1111-1111-111111111111'\n"
                "from contests c\n"
                f"where c.election_id = '22222222-2222-2222-2222-222222222222' and c.contest_label = {sql_text(label)}\n"
                "and not exists (\n"
                "  select 1 from candidates existing\n"
                "  where existing.contest_id = c.contest_id and existing.name = "
                f"{sql_text(cand_name)}\n"
                ");\n\n"
            )

        out.write(
            "insert into ballot_style_contests (ballot_style_id, contest_id)\n"
            "select '33333333-3333-3333-3333-333333333333', c.contest_id\n"
            "from contests c\n"
            f"where c.election_id = '22222222-2222-2222-2222-222222222222' and c.contest_label = {sql_text(label)}\n"
            "on conflict (ballot_style_id, contest_id) do nothing;\n\n"
        )

    print("Done.", file=sys.stderr)


if __name__ == "__main__":
    main()

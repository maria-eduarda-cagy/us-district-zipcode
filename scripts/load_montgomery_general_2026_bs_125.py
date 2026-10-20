"""Loads the real, certified general election ballot (BS 125) that applies to
Montgomery County precinct 008-006 (Ashton, MD -- same precinct as the
primary loaders). Transcribed from the official certified ballot PDF
published by the Maryland State Board of Elections:
https://elections.maryland.gov/elections/2026/general_ballots/Montgomery.pdf
(certified 2026-08-31; re-published 2026-09-03 after the Supreme Court of
Maryland order revising Question 3's language), pages 745-750.

Extracted with `pdftohtml -xml` (per-word top/left coordinates), contest by
contest. 19 contests + 3 statewide ballot questions. "or write-in" lines are
not candidates and are omitted.

Board of Education District 1/3/5: all three district seats appear on this
single precinct's ballot, because Montgomery County elects district members
countywide (the district is a residency requirement). They are therefore
loaded with scope='at_large' and no district link. The same fact resolves
the open verification_note on the primary's "Board of Education District 3"
contest (see the UPDATE at the end): the MSBE primary results
(GP26_16CouncNon-PartisanResults.csv) show District 3 votes cast in all 7
council districts, so its appearing on every ballot style was correct, not a
production error in the PDF.

Usage:
    python3 scripts/load_montgomery_general_2026_bs_125.py > out.sql
"""
import sys

SOURCE_URL = "https://elections.maryland.gov/elections/2026/general_ballots/Montgomery.pdf"
PRECINCT_CODE = "2403108-006"  # Ashton, Montgomery County (VTD from md_precincts_2026 layer)
BALLOT_STYLE_CODE = "BS 125"
SOURCE_ID = "88888888-8888-8888-8888-888888888888"
GENERAL_ELECTION_ID = "55555555-5555-5555-5555-555555555555"  # created by load_md_2026_elections_calendar.py
PRIMARY_ELECTION_ID = "22222222-2222-2222-2222-222222222222"
BALLOT_STYLE_ID = "99999999-9999-9999-9999-999999999999"
CERTIFICATION_DATE = "2026-08-31"
PUBLISHED_DATE = "2026-09-03"  # "Updated 09/03/2026" on the MSBE page; PDF Last-Modified 2026-09-04 02:59 GMT

DEM = "Democratic"
REP = "Republican"
GREEN = "Green"
WCP = "Working Class Party"

# (office_name, office_level, contest_label, district_layer_id, district_id, scope, nonpartisan, retention, vote_for, order, [(name, party), ...])
# Judges carry no party: the general ballot prints none for them (unlike the
# primary, where they were cross-filed on both party ballots).
CONTESTS = [
    ("Governor / Lieutenant Governor", "State", "Governor / Lieutenant Governor", None, None, "at_large", False, False, 1, 1, [
        ("Wes Moore / Aruna Miller", DEM),
        ("Dan Cox / Rob Krop", REP),
        ("Andy Ellis / Owen Silverman Andrews", GREEN),
        ("Cathy White / Cathy Permut", WCP),
    ]),
    ("Comptroller", "State", "Comptroller", None, None, "at_large", False, False, 1, 2, [
        ("Brooke Elizabeth Lierman", DEM),
        ("Sonya Dunn", REP),
    ]),
    ("Attorney General", "State", "Attorney General", None, None, "at_large", False, False, 1, 3, [
        ("Anthony G. Brown", DEM),
        ("James B. Rutledge, III", REP),
    ]),
    ("U.S. Representative", "Federal", "Representative in Congress District 8", "cd119", "2408", "district", False, False, 1, 4, [
        ("Jamie Raskin", DEM),
        ("Cheryl Riley", REP),
        ("Nancy Wallace", GREEN),
    ]),
    ("State Senator", "State", "State Senator District 14", "sldu", "24014", "district", False, False, 1, 5, [
        ("Craig J. Zucker", DEM),
    ]),
    ("House of Delegates", "State", "House of Delegates District 14", "md_delegate_subdistricts_2022", "14", "district", False, False, 3, 6, [
        ("Anne R. Kaiser", DEM),
        ("Bernice Mireku-North", DEM),
        ("Matt Post", DEM),
    ]),
    ("County Executive", "Local", "County Executive", "county", "24031", "at_large", False, False, 1, 7, [
        ("Will Jawando", DEM),
        ("Esther Wells", REP),
    ]),
    ("County Council", "Local", "County Council At-Large", "county", "24031", "at_large", False, False, 4, 8, [
        ("Marc Elrich", DEM),
        ("Scott Evan Goldberg", DEM),
        ("Laurie-Anne Sayles", DEM),
        ("Karla Silvestre", DEM),
        ("Sherwin Wells", REP),
    ]),
    ("County Council", "Local", "County Council District 7", "md_montgomery_council_districts", "7", "district", False, False, 1, 9, [
        ("Dawn Luedtke", DEM),
        ("Harold Maldonado", REP),
    ]),
    ("Judge of the Circuit Court", "Local", "Judge of the Circuit Court Circuit 6", None, None, "at_large", False, False, 4, 10, [
        ("Sharon V. Burrell", None),
        ("Victor M. Del Pino", None),
        ("James J. Dietrich", None),
        ("Catherine H. McQueen", None),
    ]),
    ("Judge, Appellate Court of Maryland", "State", "Judge, Appellate Court of Maryland At Large", None, None, "at_large", False, True, 1, 11, [
        ("Dan Friedman", None),
    ]),
    ("State's Attorney", "Local", "State's Attorney", "county", "24031", "at_large", False, False, 1, 12, [
        ("John McCarthy", DEM),
    ]),
    ("Clerk of the Circuit Court", "Local", "Clerk of the Circuit Court", "county", "24031", "at_large", False, False, 1, 13, [
        ("Karen Bushell", DEM),
    ]),
    ("Register of Wills", "Local", "Register of Wills", "county", "24031", "at_large", False, False, 1, 14, [
        ("Barbara Ebel", DEM),
        ("T. Dolores Reyes", REP),
    ]),
    ("Sheriff", "Local", "Sheriff", "county", "24031", "at_large", False, False, 1, 15, [
        ("Will Milam", DEM),
    ]),
    ("Board of Education", "Local", "Board of Education At-Large", "county", "24031", "at_large", True, False, 1, 16, [
        ("Brenda M. Diaz", None),
        ("Omar Lazo", None),
    ]),
    ("Board of Education", "Local", "Board of Education District 1", None, None, "at_large", True, False, 1, 17, [
        ("Grace Rivera-Oven", None),
    ]),
    ("Board of Education", "Local", "Board of Education District 3", None, None, "at_large", True, False, 1, 18, [
        ("Sally A. McCarthy", None),
        ('Cassandra "Cassi" Sung', None),
    ]),
    ("Board of Education", "Local", "Board of Education District 5", None, None, "at_large", True, False, 1, 19, [
        ("Elma-Lorraine Diggs", None),
    ]),
]

# (measure_id, order, title, question_text, impact_yes, impact_no)
# Question 3 is printed without FOR/AGAINST explanations (its language was
# replaced per the 2026-09-03 court order), so those stay null.
MEASURES = [
    (
        "aaaaaaaa-aaaa-aaaa-aaaa-000000000001", 1,
        "Question 1 - Constitutional Amendment (Ch. 155 of the 2026 Legislative Session): "
        "Arbitration Reform for State Employees Act of 2026",
        "Providing that each budget submitted by the Governor shall include proposed expenditures necessary to "
        "implement wages, hours, fringe benefits, health benefits, and other terms and conditions of employment in "
        "each collective bargaining memorandum of understanding with State employees, whether the State and State "
        "employees reached those terms and conditions by mutual agreement or through a neutral decider's order. "
        "(Amending Article III of the Maryland Constitution)",
        "A vote FOR this amendment means that the Governor has to include money in the proposed State budget to pay "
        "for agreements between the State and its employees. Agreements might include changes to wages, hours, "
        "fringe benefits, health benefits, and other terms and conditions of employment. The Governor must put "
        "enough money in the State budget to cover the agreed upon pay and benefits for employees, whether those "
        "terms were negotiated or decided by a neutral decision-maker.",
        "A vote AGAINST the amendment means that the law about funding agreements between the State and State "
        "employees stays the same.",
    ),
    (
        "aaaaaaaa-aaaa-aaaa-aaaa-000000000002", 2,
        "Question 2 - Constitutional Amendment (Ch. 878 of the 2026 Legislative Session): "
        "Temporary Appointments on the Commission on Judicial Disabilities",
        "Authorizing temporary substitute appointments to the Commission on Judicial Disabilities when a member is "
        "recused or disqualified, or when a member's term expires. In these situations, the Commission Chair may "
        "recall a former member of the Commission, or the Governor, at the request of the Commission Chair, may "
        "appoint a temporary substitute member or extend the term of a current member until a permanent replacement "
        "is appointed. Only individuals who meet the constitutional eligibility requirements may be recalled or "
        "appointed to the Commission. (Amending Article IV of the Maryland Constitution)",
        "A vote FOR this amendment means that temporary appointments to the Commission are allowed if a member is "
        "recused, disqualified, or if a member's term ends without a replacement. The Commission Chair can "
        "temporarily fill an opening on the Commission with a former member. The Governor can, at the request of the "
        "Commission Chair, pick a temporary substitute to fill an opening on the Commission or extend the term of a "
        "current member until a replacement is appointed. Only individuals who meet the constitutional eligibility "
        "requirements may be recalled or appointed to the Commission.",
        "A vote AGAINST the amendment means that current membership rules for the Commission stay the same. "
        "Temporary appointments are not allowed if a member is recused, disqualified, or if a member's term ends.",
    ),
    (
        "aaaaaaaa-aaaa-aaaa-aaaa-000000000003", 3,
        "Question 3 - Constitutional Amendment (Ch. 881 of the 2026 Legislative Session): "
        "Election Districts - General Assembly and Representatives in Congress",
        "FOR the purpose of clarifying that certain requirements apply only to districts for the election of members "
        "of the Senate of Maryland and the House of Delegates; authorizing the General Assembly to grant original "
        "jurisdiction to the Supreme Court of Maryland to review the congressional districting plan of the State; "
        "and providing that nothing in the Maryland Constitution provides applicable criteria for the boundaries of "
        "a congressional districting plan. (Amending Article III of the Maryland Constitution)",
        None,
        None,
    ),
]


def dq(value: str, tag: str = "q") -> str:
    return f"${tag}${value}${tag}$"


def sql_text(value):
    return "null" if value is None else dq(str(value))


def sql_bool(value: bool) -> str:
    return "true" if value else "false"


def main():
    out = sys.stdout
    out.write("-- Generated by scripts/load_montgomery_general_2026_bs_125.py. Idempotent: safe to re-run.\n\n")

    out.write(
        "insert into sources (source_id, source_url, source_type, effective_date, confidence, notes)\n"
        f"values ('{SOURCE_ID}', {sql_text(SOURCE_URL)}, {sql_text('certified_ballot_pdf')}, "
        f"'{PUBLISHED_DATE}', 1.0, "
        f"{sql_text('Maryland SBE certified general ballot, Montgomery County (certified 2026-08-31, updated 2026-09-03)')})\n"
        "on conflict (source_id) do update set fetched_at = now(), effective_date = excluded.effective_date;\n\n"
    )

    out.write(
        "insert into ballot_styles (ballot_style_id, election_id, precinct_id, party, style_code, "
        "sample_ballot_url, certification_date, source_id)\n"
        f"select '{BALLOT_STYLE_ID}', '{GENERAL_ELECTION_ID}', "
        f"p.precinct_id, null, {sql_text(BALLOT_STYLE_CODE)}, {sql_text(SOURCE_URL)}, "
        f"'{CERTIFICATION_DATE}', '{SOURCE_ID}'\n"
        f"from precincts p where p.precinct_code = {sql_text(PRECINCT_CODE)} and p.state = 'MD'\n"
        "on conflict (ballot_style_id) do nothing;\n\n"
    )

    for (office_name, level, label, layer_id, district_id, scope, nonpartisan, retention, vote_for, order,
         candidates) in CONTESTS:
        out.write(
            "insert into offices (name, level, description)\n"
            f"values ({sql_text(office_name)}, {sql_text(level)}, {sql_text(office_name)})\n"
            "on conflict (name, level) do nothing;\n\n"
        )

        out.write(
            "insert into contests (election_id, office_id, district_layer_id, district_id, contest_label, "
            "scope, nonpartisan, retention, write_in_allowed, vote_for, order_on_ballot, source_id)\n"
            f"select '{GENERAL_ELECTION_ID}', o.office_id, "
            f"{sql_text(layer_id)}, {sql_text(district_id)}, {sql_text(label)}, {sql_text(scope)}, "
            f"{sql_bool(nonpartisan)}, {sql_bool(retention)}, {sql_bool(not retention)}, {vote_for}, {order}, "
            f"'{SOURCE_ID}'\n"
            f"from offices o where o.name = {sql_text(office_name)} and o.level = {sql_text(level)}\n"
            "on conflict (election_id, office_id, coalesce(district_id, ''), contest_label) do update\n"
            "  set vote_for = excluded.vote_for, scope = excluded.scope, nonpartisan = excluded.nonpartisan,\n"
            "      retention = excluded.retention, order_on_ballot = excluded.order_on_ballot;\n\n"
        )

        # Only as many candidates as seats (or fewer): nobody to beat. Retention
        # races are yes/no on a single judge, so "unopposed" doesn't apply.
        unopposed = not retention and len(candidates) <= vote_for
        for i, (cand_name, party) in enumerate(candidates, start=1):
            out.write(
                "insert into candidates (contest_id, name, party, unopposed, ballot_order, source_id)\n"
                "select c.contest_id, "
                f"{sql_text(cand_name)}, {sql_text(party)}, {sql_bool(unopposed)}, {i}, '{SOURCE_ID}'\n"
                "from contests c\n"
                f"where c.election_id = '{GENERAL_ELECTION_ID}' and c.contest_label = {sql_text(label)}\n"
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
            f"where c.election_id = '{GENERAL_ELECTION_ID}' and c.contest_label = {sql_text(label)}\n"
            "on conflict (ballot_style_id, contest_id) do nothing;\n\n"
        )

    for measure_id, order, title, question_text, impact_yes, impact_no in MEASURES:
        out.write(
            "insert into ballot_measures (measure_id, election_id, jurisdiction_scope, title, question_text, "
            "impact_yes, impact_no, order_on_ballot, source_id)\n"
            f"values ('{measure_id}', '{GENERAL_ELECTION_ID}', 'state', {sql_text(title)}, {sql_text(question_text)}, "
            f"{sql_text(impact_yes)}, {sql_text(impact_no)}, {order}, '{SOURCE_ID}')\n"
            "on conflict (measure_id) do update set title = excluded.title, question_text = excluded.question_text,\n"
            "  impact_yes = excluded.impact_yes, impact_no = excluded.impact_no;\n\n"
        )
        out.write(
            "insert into ballot_style_measures (ballot_style_id, measure_id)\n"
            f"values ('{BALLOT_STYLE_ID}', '{measure_id}')\n"
            "on conflict (ballot_style_id, measure_id) do nothing;\n\n"
        )

    # The calendar loader wrote this note on 2026-07-02, before certification.
    out.write(
        "update deadlines set notes = "
        f"{sql_text('polls close 8pm; ballot certified 2026-08-31, Question 3 language revised 2026-09-03')}\n"
        f"where election_id = '{GENERAL_ELECTION_ID}' and deadline_type = 'election_day';\n\n"
    )

    # See module docstring: District 3 was elected countywide in the primary.
    out.write(
        "update contests set scope = 'at_large', verification_note = null\n"
        f"where election_id = '{PRIMARY_ELECTION_ID}' and contest_label = {sql_text('Board of Education District 3')};\n\n"
    )

    print("Done.", file=sys.stderr)


if __name__ == "__main__":
    main()

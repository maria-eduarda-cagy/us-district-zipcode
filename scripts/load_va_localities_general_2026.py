"""Loads the 2026 general election ballot for Northern Virginia localities
other than Fairfax County (which has its own loader), on top of the
precincts loaded by load_va_precincts.py (precinct code = county FIPS +
"000" + precinct number, e.g. 51153000208).

Each locality's ballot styles are transcribed from its official sample
ballots and checked against Virginia ELECT's candidate lists. The contests
and amendments every locality shares (U.S. Senate, U.S. House, the 3
constitutional amendments) come from va_general_2026.py, so they are the same
rows Fairfax's ballots link to.

Localities:
- Alexandria (https://www.alexandriava.gov/elections/sample-ballots, one
  sample ballot for the whole city, dated 2026-08-25): U.S. Senate, House
  8th District, the 3 amendments. No local contests or questions. Its PDF
  text is font-shifted by 29 code points (pdftotext gives "0DUN5:DUQHU" for
  "Mark R. Warner"); decoded, names, parties and order match the Fairfax
  8th District ballot.
- Prince William (https://www.pwcvotes.org/ontheballot, one sample ballot
  per precinct plus town and House District 20 ballots; the page also still
  lists 2025 ballots, ignored). Every ballot: U.S. Senate, House 7th or 10th
  District, the 3 amendments; no county questions. Precinct -> congressional
  district comes from each precinct's ballot and agrees with the cd119
  geometry for all 96 single-district precincts. Colgan (208) is split 7/10
  and gets both styles. Precincts 204, 211, 212, 213 and 408 also have the
  House of Delegates District 20 special election. The 4 towns' contests are
  on separate "town residents only" ballots, so the precincts they lie in
  (Dumfries 301, Haymarket 409, Occoquan 502, Quantico 304) get a town and a
  non-town style, told apart by the `place` layer as in Herndon. 706-711 have
  no November ballot on the page (only a March 2026 special); they lie 100% in
  the 7th District with no town or special contest, so they get the standard
  7th District ballot, which is fully determined by those districts.

Usage:
    python3 scripts/load_va_localities_general_2026.py > out.sql
"""
import os
import sys
import uuid

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from va_general_2026 import (  # noqa: E402
    AMENDMENT_EXPLANATIONS, AMENDMENTS, DEM, ELECTION_ID, FEDERAL_CONTESTS, NS, REP, measure_id,
)

AMENDMENT_KEYS = ["q1", "q2", "q3"]

PW_TOWNS = {  # town -> (TIGER place GEOID, precinct, congressional district, mayor candidates, council seats, council candidates)
    "Dumfries": ("5123760", "301", "7", ["Brian K. Fields", "Derrick R. Wood"], 3, [
        "Caetrina A. Peterson", "Monae' S. Nickerson", "Selonia Bernice Miles", "Ebony Evonne Lofton", "Tyrone Brown",
    ]),
    "Haymarket": ("5135976", "409", "10", ["Tracy Lynn Pater"], 6, [
        "David L. Capossela", "Matthew J. Gallagher", 'Kenneth M. "Ken" Luersen', 'Joseph R. "Joe" Pasanello',
        "Jen Armstrong Schenck",
    ]),
    "Occoquan": ("5158696", "502", "7", ["Earnie W. Porta, Jr."], 5, [
        "Jenn M. Loges", 'Robert E. "Bob" Love', "Eliot R. Perkins",
    ]),
    "Quantico": ("5165120", "304", "7", ["Kevin P. Brown", "Jennifer L. Stoltz"], 5, [
        "Sammoto Yomosa Dabney", 'Shanon "Red" Sullivan', "Robert Teron Freeman", 'Jason R. "Jae" Stoltz',
        'S. "Steve" Kang', "Brandi M. Maly", "Nadia Madjid", 'Ingrid S. "Suzi" Nedrow', "Samuel Cachola, Jr.",
        "Todd D. Zirkle",
    ]),
}
PW_PRECINCTS_BY_CD = {
    "7": [
        "201", "207", "215", "301", "302", "303", "304", "305", "306", "307", "308", "309",
        "310", "311", "312", "313", "314", "315", "316", "501", "502", "503", "504", "505",
        "506", "507", "510", "511", "512", "513", "514", "516", "601", "602", "603", "604",
        "605", "606", "607", "608", "609", "610", "611", "612", "613", "614", "615", "616",
        "701", "702", "703", "704", "705", "706", "707", "708", "709", "710", "711", "712",
    ],
    "10": [
        "101", "102", "103", "104", "105", "106", "107", "108", "109", "110", "111", "112",
        "113", "114", "202", "203", "204", "205", "206", "209", "210", "211", "212", "213",
        "214", "401", "402", "403", "404", "405", "406", "407", "408", "409", "410", "411",
        "412", "413", "414", "508", "509", "515",
    ],
}
PW_SPLIT_CD = {"208": ["7", "10"]}  # Colgan
PW_HD20 = {"204", "211", "212", "213", "408"}


def pw_config():
    contests = {
        "hd20": ("House of Delegates", "State", "Member House of Delegates 20th District", "sldl", "51020", "district",
                 False, 1, 3, [("Sonia Ruth Vasquez Luna", DEM), ('Nathaniel "Nate" Fritzen', REP)]),
    }
    styles = {
        "7th CD": (["senate", "house7"], AMENDMENT_KEYS),
        "10th CD": (["senate", "house10"], AMENDMENT_KEYS),
        "10th CD + House District 20": (["senate", "house10", "hd20"], AMENDMENT_KEYS),
    }
    for town, (place, _, cd, mayors, seats, council) in PW_TOWNS.items():
        contests[f"mayor_{town}"] = ("Mayor", "Local", f"Mayor Town of {town}", "place", place, "district",
                                     True, 1, 4, [(n, None) for n in mayors])
        contests[f"council_{town}"] = ("Town Council", "Local", f"Member Town Council Town of {town}", "place", place,
                                       "district", True, seats, 5, [(n, None) for n in council])
        styles[f"Town of {town}"] = (["senate", f"house{cd}", f"mayor_{town}", f"council_{town}"], AMENDMENT_KEYS)

    def base(cd, precinct):
        return "10th CD + House District 20" if precinct in PW_HD20 else f"{cd}th CD"

    precinct_styles = {}
    for cd, precincts in PW_PRECINCTS_BY_CD.items():
        for p in precincts:
            precinct_styles[p] = [base(cd, p)]
    for p, cds in PW_SPLIT_CD.items():
        precinct_styles[p] = [base(cd, p) for cd in cds]
    for town, (_, precinct, *_rest) in PW_TOWNS.items():
        precinct_styles[precinct].append(f"Town of {town}")
    assert len(precinct_styles) == 103, len(precinct_styles)
    return contests, styles, precinct_styles


PW_CONTESTS, PW_STYLES, PW_PRECINCT_STYLES = pw_config()

# name -> county FIPS, source, its date, local contests (same tuple format as
# FEDERAL_CONTESTS), styles: style_code -> (contest keys, measure keys), and
# precinct number -> styles (None: every precinct gets the only style).
LOCALITIES = {
    "Alexandria": {
        "fips": "51510",
        "source_url": "https://www.alexandriava.gov/sites/default/files/2026-08/"
                      "2026_Nov_Sample%20Ballot_Colored%20Background_for%20posting.pdf",
        "published": "2026-08-25",
        "contests": {},
        "styles": {"Alexandria": (["senate", "house8"], AMENDMENT_KEYS)},
        "precinct_styles": None,
    },
    "Prince William": {
        "fips": "51153",
        "source_url": "https://www.pwcvotes.org/ontheballot",
        "published": "2026-10-21",  # page as fetched; the PDFs carry no date
        "contests": PW_CONTESTS,
        "styles": PW_STYLES,
        "precinct_styles": PW_PRECINCT_STYLES,
    },
}


def dq(value: str, tag: str = "q") -> str:
    return f"${tag}${value}${tag}$"


def sql_text(value):
    return "null" if value is None else dq(str(value))


def sql_bool(value: bool) -> str:
    return "true" if value else "false"


def contest_sql(contest, source_id: str) -> str:
    office, level, label, layer, district, scope, nonpartisan, vote_for, order, candidates = contest
    sql = (
        "insert into offices (name, level, description)\n"
        f"values ({sql_text(office)}, {sql_text(level)}, {sql_text(office)})\n"
        "on conflict (name, level) do nothing;\n\n"
        "insert into contests (election_id, office_id, district_layer_id, district_id, contest_label, "
        "scope, nonpartisan, retention, write_in_allowed, vote_for, order_on_ballot, source_id)\n"
        f"select '{ELECTION_ID}', o.office_id, {sql_text(layer)}, {sql_text(district)}, {sql_text(label)}, "
        f"{sql_text(scope)}, {sql_bool(nonpartisan)}, false, true, {vote_for}, {order}, '{source_id}'\n"
        f"from offices o where o.name = {sql_text(office)} and o.level = {sql_text(level)}\n"
        "on conflict (election_id, office_id, coalesce(district_id, ''), contest_label) do nothing;\n\n"
    )
    unopposed = len(candidates) <= vote_for
    for i, (cand, party) in enumerate(candidates, start=1):
        sql += (
            "insert into candidates (contest_id, name, party, unopposed, ballot_order, source_id)\n"
            f"select c.contest_id, {sql_text(cand)}, {sql_text(party)}, {sql_bool(unopposed)}, {i}, c.source_id\n"
            f"from contests c where c.election_id = '{ELECTION_ID}' and c.contest_label = {sql_text(label)}\n"
            f"and not exists (select 1 from candidates k where k.contest_id = c.contest_id and k.name = {sql_text(cand)});\n\n"
        )
    return sql


def main():
    out = sys.stdout
    out.write("-- Generated by scripts/load_va_localities_general_2026.py. Idempotent: safe to re-run.\n\n")
    amendments = {key: rest for key, *rest in AMENDMENTS}

    for name, loc in LOCALITIES.items():
        fips = loc["fips"]
        source_id = str(uuid.uuid5(NS, loc["source_url"]))
        contests = {**FEDERAL_CONTESTS, **loc["contests"]}
        out.write(f"-- {name}\n")
        out.write(
            "insert into sources (source_id, source_url, source_type, effective_date, confidence, notes)\n"
            f"values ('{source_id}', {sql_text(loc['source_url'])}, 'sample_ballot_pdf', '{loc['published']}', 1.0, "
            f"{sql_text(f'{name} sample ballots, 2026 general election')})\n"
            "on conflict (source_id) do update set fetched_at = now(), effective_date = excluded.effective_date;\n\n"
            # Normally created by the Fairfax loader already.
            "insert into elections (election_id, name, election_type, election_date, state, jurisdiction_scope, "
            "party_scope, is_special, status, source_id)\n"
            f"values ('{ELECTION_ID}', '2026 General Election', 'general', '2026-11-03', 'VA', 'state', null, false, "
            f"'scheduled', '{source_id}')\n"
            "on conflict (election_id) do nothing;\n\n"
        )
        for key in sorted({k for keys, _ in loc["styles"].values() for k in keys}):
            out.write(contest_sql(contests[key], source_id))
        for key in sorted({k for _, keys in loc["styles"].values() for k in keys}):
            order, scope, layer, district, title, question = amendments[key]
            explanation_url, explanation = AMENDMENT_EXPLANATIONS[key]
            out.write(
                "insert into ballot_measures (measure_id, election_id, district_layer_id, district_id, jurisdiction_scope, "
                "title, question_text, explanation, explanation_source_url, order_on_ballot, source_id)\n"
                f"values ('{measure_id(key)}', '{ELECTION_ID}', {sql_text(layer)}, {sql_text(district)}, '{scope}', "
                f"{sql_text(title)}, {sql_text(question)}, {sql_text(explanation)}, {sql_text(explanation_url)}, "
                f"{order}, '{source_id}')\n"
                "on conflict (measure_id) do nothing;\n\n"
            )

        if loc["precinct_styles"] is None:
            (only_style,) = loc["styles"]
            rows_sql = (f"select p.precinct_id, {sql_text(only_style)} as style_code from precincts p "
                        f"where p.state = 'VA' and p.county_fips = '{fips}'")
        else:
            values = ",\n".join(f"  ('{fips}000{p}', {sql_text(s)})"
                                for p, styles in sorted(loc["precinct_styles"].items()) for s in styles)
            rows_sql = (f"select p.precinct_id, v.style_code from (values\n{values}\n) v(precinct_code, style_code)\n"
                        f"join precincts p on p.precinct_code = v.precinct_code and p.state = 'VA'")
        out.write(
            # Rebuilt for the locality: style assignments can change between runs.
            "delete from ballot_styles bs using precincts p where bs.precinct_id = p.precinct_id "
            f"and bs.election_id = '{ELECTION_ID}' and p.state = 'VA' and p.county_fips = '{fips}';\n\n"
            "insert into ballot_styles (election_id, precinct_id, party, style_code, sample_ballot_url, source_id)\n"
            f"select '{ELECTION_ID}', r.precinct_id, null, r.style_code, {sql_text(loc['source_url'])}, '{source_id}'\n"
            f"from ({rows_sql}) r;\n\n"
        )
        for style, (contest_keys, measure_keys) in loc["styles"].items():
            labels = ", ".join(sql_text(contests[k][2]) for k in contest_keys)
            ids = ", ".join(f"'{measure_id(k)}'::uuid" for k in measure_keys)
            style_filter = (f"bs.election_id = '{ELECTION_ID}' and bs.style_code = {sql_text(style)} "
                            f"and p.state = 'VA' and p.county_fips = '{fips}'")
            out.write(
                "insert into ballot_style_contests (ballot_style_id, contest_id)\n"
                "select bs.ballot_style_id, c.contest_id\n"
                "from ballot_styles bs join precincts p using (precinct_id)\n"
                f"join contests c on c.election_id = bs.election_id and c.contest_label in ({labels})\n"
                f"where {style_filter}\n"
                "on conflict (ballot_style_id, contest_id) do nothing;\n\n"
                "insert into ballot_style_measures (ballot_style_id, measure_id)\n"
                "select bs.ballot_style_id, m.measure_id\n"
                "from ballot_styles bs join precincts p using (precinct_id)\n"
                f"join ballot_measures m on m.measure_id in ({ids})\n"
                f"where {style_filter}\n"
                "on conflict (ballot_style_id, measure_id) do nothing;\n\n"
            )
        expected = (sum(len(s) for s in loc["precinct_styles"].values())
                    if loc["precinct_styles"] is not None else None)
        out.write(
            "do $$ begin\n"
            f"  if exists (select 1 from precincts p where p.state = 'VA' and p.county_fips = '{fips}' "
            f"and not exists (select 1 from ballot_styles bs where bs.precinct_id = p.precinct_id "
            f"and bs.election_id = '{ELECTION_ID}')) then\n"
            f"    raise exception '{name}: a precinct got no ballot style';\n"
            "  end if;\n"
            + (f"  if (select count(*) from ballot_styles bs join precincts p using (precinct_id) "
               f"where bs.election_id = '{ELECTION_ID}' and p.county_fips = '{fips}') <> {expected} then\n"
               f"    raise exception '{name}: expected {expected} ballot styles (a precinct code did not match)';\n"
               "  end if;\n" if expected is not None else "")
            + "end $$;\n\n"
        )
    print("Done.", file=sys.stderr)


if __name__ == "__main__":
    main()

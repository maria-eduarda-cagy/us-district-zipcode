"""Loads the 2026 general election ballot for every precinct in Fairfax County,
VA, transcribed from the county's official sample ballots
(https://www.fairfaxcounty.gov/elections/sample-ballots, PDFs dated
2026-09-02):

    2026_November_08thCD_Full.pdf                  -> "8th CD Full"
    2026_November_10thCD_Full.pdf                  -> "10th CD Full"
    2026_November_11thCD_Full.pdf                  -> "11th CD Full"
    2026_November_11thCD_Herndon_Full.pdf          -> "Herndon Full"
    2026_November_11thCD_Herndon_Town_Exception.pdf -> "Herndon Town Exception"

The "Federal Only" PDFs are skipped: they are for voters restricted to federal
races (e.g. moved out of state), which an address can't tell us. The Town
Exception ballot is word-for-word the 11th CD Full ballot; it is what voters
in a Herndon precinct who live outside the town limits get.

Every Fairfax ballot has U.S. Senate, one House race, the 3 Virginia
constitutional amendments and 2 county bond questions; Herndon adds Mayor and
Town Council. So a precinct's style only depends on its congressional
district and on being one of the Herndon precincts.

Precinct -> congressional district comes from the county's precinct
descriptions (https://www.fairfaxcounty.gov/elections/precincts, one PDF per
supervisor district plus Precinct_527v2/Precinct_858_v3), not from geometry:
TIGER's cd119 and even the county's own CD layer disagree with the precinct
layer at the edges by up to ~14% of a precinct's area. The descriptions list
exactly the 266 precincts in the GIS layer, and agree with the majority
overlap of the county CD layer for all but Pioneer (409), which is officially
split 11/8 and gets both styles; sample-ballot picks the one matching the
address's CD. Herndon #1/#2/#3 likewise get both Herndon styles.

The 2026 redistricting referendum (approved 2026-04-21) was voided by the
Supreme Court of Virginia on 2026-05-08, so the 2021 congressional map stands.

Precincts must be loaded first (district_boundaries layer
va_fairfax_precincts, from load_district_layers.py); this script copies them
into `precincts`.

Usage:
    python3 scripts/load_fairfax_general_2026.py > out.sql
"""
import os
import sys
import uuid

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from va_general_2026 import (  # noqa: E402
    AMENDMENT_EXPLANATIONS, AMENDMENTS, ELECTION_ID, FEDERAL_CONTESTS, NS, measure_id,
)

PDF_BASE = "https://www.fairfaxcounty.gov/elections/sites/elections/files/Assets/Documents/PDF/"
PUBLISHED_DATE = "2026-09-02"  # Last-Modified of every sample ballot PDF
COUNTY_FIPS = "51059"
HERNDON_PLACE = "5136648"

# style_code -> (pdf, contest keys)
STYLES = {
    "8th CD Full": ("2026_November_08thCD_Full.pdf", ["senate", "house8"]),
    "10th CD Full": ("2026_November_10thCD_Full.pdf", ["senate", "house10"]),
    "11th CD Full": ("2026_November_11thCD_Full.pdf", ["senate", "house11"]),
    "Herndon Full": ("2026_November_11thCD_Herndon_Full.pdf", ["senate", "house11", "mayor", "council"]),
    "Herndon Town Exception": ("2026_November_11thCD_Herndon_Town_Exception.pdf", ["senate", "house11"]),
}

# key -> (office_name, office_level, contest_label, district_layer_id, district_id, scope, nonpartisan, vote_for, order, [(name, party), ...])
CONTESTS = {
    **FEDERAL_CONTESTS,
    "mayor": ("Mayor", "Local", "Mayor Town of Herndon", "place", HERNDON_PLACE, "district", True, 1, 3, [
        ("Keven J LeBlanc, Jr", None),
    ]),
    "council": ("Town Council", "Local", "Member Town Council Town of Herndon", "place", HERNDON_PLACE, "district", True, 6, 4, [
        ("Josif N. Ezekilov", None),
        ("Cesar A. Del Aguila", None),
        ('Douglas Isaac "Doug" Mejia', None),
        ("Sabrina A. Bruce", None),
        ("Kelvin Garcia", None),
        ('Yasmin "Soniya" Shafiq', None),
        ("Meron T. Yohannes", None),
        ("Clark A. Hedrick", None),
        ("Michael T. Lloyd", None),
        ("Justin K. Britt", None),
        ('Alexis "Alex" Reyes', None),
        ("Stevan Michael Porter", None),
    ]),
}

# (key, order, jurisdiction_scope, district_layer_id, district_id, title, question_text)
# On every style. The ballot prints no FOR/AGAINST explanations, so
# impact_yes/impact_no stay null; the official explanations published
# separately go in `explanation` (see EXPLANATIONS).
MEASURES = AMENDMENTS + [
    ("parks", 4, "county", "county", COUNTY_FIPS, "Fairfax County Bond Issue - Parks and Park Facilities Bonds",
     "Shall Fairfax County, Virginia, contract a debt, borrow money, and issue bonds, in addition to the parks and "
     "park facilities bonds previously authorized, in the maximum aggregate principal amount of $180,000,000 for "
     "the purpose of providing funds, with any other available funds, to finance, including reimbursement to the "
     "County for temporary financing for, the Fairfax County Park Authority’s cost to acquire, construct, "
     "develop, and equip additional parks and park facilities, to preserve open-space land, and to develop and "
     "improve existing parks and park facilities?"),
    ("health", 5, "county", "county", COUNTY_FIPS,
     "Fairfax County Bond Issue - Community Health and Human Services Facilities Bonds",
     "Shall Fairfax County, Virginia, contract a debt, borrow money, and issue bonds, in addition to the community "
     "health and human services facilities bonds previously authorized, in the maximum aggregate principal amount "
     "of $75,000,000 for the purpose of providing funds, with any other available funds, to finance, including "
     "reimbursement to the County for temporary financing for, the cost to provide community health and human "
     "services facilities, including the construction, reconstruction, enlargement, and equipment of existing and "
     "additional community health and human services facilities and the acquisition of necessary land?"),
]

# measure key -> (source_url, explanation). Verbatim: the "Present Law" /
# "Proposed Law" sections of Virginia ELECT's explanation of each amendment,
# and the "Explanation" of each county bond statement (Va. Code 24.2-687). The
# bond PDFs print some compound words without their hyphen ("11,800squarefoot",
# "COVID19"); kept as printed. Paragraphs are separated by a blank line.
EXPLANATIONS = {
    **AMENDMENT_EXPLANATIONS,
    "parks": (
        "https://www.fairfaxcounty.gov/bond/sites/bond/files/Assets/Documents/2026%20Plain%20Language%20Statements/Parks%20PLS%20Web%20English.pdf",
        "This referendum asks voters whether Fairfax County should be authorized to contract a debt and issue bonds in the maximum principal amount of $180,000,000 for improvement of existing parks owned and operated by Fairfax County Park Authority, for additional parks and recreational facilities, and for preservation of open space across the county. The County’s current plans for the proceeds of bonds that may be authorized by this referendum are described below. These specific plans may be altered, but in any case, the bonds can only be issued for purposes described in the ballot question.\n\n"
        "Virginia law permits the County government to borrow money to buy land and construct projects by issuing general obligation bonds, which are sold to investors and repaid over time with County revenues. Money received from the sale of bonds provides funding for many County facilities. Bond financing permits the costs of those County facilities to be repaid over a period of years. However, before the County may incur a general obligation debt, a majority of the County voters must authorize the County to borrow those funds.\n\n"
        "The County currently plans to use $180,000,000 of bonds from this referendum for Fairfax County Park Authority system improvements and facilities. Funding from this referendum will support a range of capital projects across the county with current plans addressing existing maintenance needs, design and construction of new parks and amenities, preservation of natural and historic resources, and renovation of park and rec center facilities in need of lifecycle replacement.\n\n"
        "Currently planned projects include entirely new parks and new amenities in existing parks, such as playgrounds, skateparks, or trails. Funding will address repair, replacement, and upgrade of current park facilities, improving service and access, and modernizing outdated amenities, such as playgrounds, picnic shelters, trails, amusements, athletic fields, athletic courts, support facilities, and infrastructure such as lighting and irrigation to current standards and codes.\n\n"
        "Capital funding for Rec Center renovations will support design, repairs, upgrades, and capital improvements to maintain safety, functionality, accessibility, and service quality. Projects will include lifecycle replacements to repair, replace, and modernize amenities covering structural, mechanical, electrical, and cosmetic systems, such as HVAC systems, pool pump equipment, and roofing. This funding is currently planned to support the complete renovation of Audrey Moore Rec Center, deferred maintenance at other Rec Centers, and concept plans for future renovations of additional Rec Centers.\n\n"
        "The bond referendum will fund projects such as ecological restorations including meadow restoration, expansion and reforestation projects; historic site preservation projects focusing on structural needs, systems preservation, infrastructure and stabilization work on historic structures; maintenance and preservation work for historic cemeteries in parks; and parkland acquisition.",
    ),
    "health": (
        "https://www.fairfaxcounty.gov/bond/sites/bond/files/Assets/Documents/2026%20Plain%20Language%20Statements/CHHS%20PLS%20Web%20English.pdf",
        "This referendum asks voters whether Fairfax County should be authorized to contract a debt and issue bonds in the maximum principal amount of $75,000,000 for community health and human services facilities. The County’s current plans for the proceeds of bonds that may be authorized by this referendum are set forth below. These specific plans may be altered, but in any case, the bonds can only be issued for purposes described in the ballot question.\n\n"
        "Virginia law permits the County government to borrow money to buy land, purchase capital equipment, and construct or improve facilities by issuing general obligation bonds, which are sold to investors and repaid over time with County revenues. Money received from the sale of bonds provides funding for many County facilities. Bond financing permits the costs of those County facilities to be repaid over a period of years. However, before the County may incur a general obligation debt, a majority of the County voters must authorize the County to borrow those funds.\n\n"
        "The County currently plans to use $35,000,000 in bonds to renovate or replace the Joanne Jorgenson Public Health Laboratory, located in the former Belle Willard School building. The current 11,800squarefoot facility includes Biosafety Level 2 and Level 3 laboratories. In 2020, the County added a 1,500squarefoot modular lab to expand Biosafety Level 2 testing capacity in response to the COVID19 pandemic and address space constraints. The laboratory is the only local public health laboratory in Virginia and performs more than 200,000 tests each year for Fairfax County and surrounding communities. Renovation or replacement of the laboratory will expand the existing facility to integrate the modular lab’s space and expand future testing capacity. The integrated design will focus on improving operational efficiency, flexibility, and readiness to address future public health, environmental, and clinical testing needs and support emergency response activities.\n\n"
        "Current plans also include using $40,000,000 in bonds to renovate or replace facilities supporting three programs at the Tim Harmon Campus: A New Beginning, Fairfax Detox Center, and the Cornerstone Facility. A New Beginning provides residential treatment programs for adults with substance use disorders and co-occurring mental health challenges. Fairfax Detox Center is a 32-bed residential program offering a safe, structured environment for individuals detoxing from alcohol or drugs. The Cornerstone Facility was repurposed as a Northern Virginia Adolescent Treatment Center, which is a 16-bed residential treatment center for youth with cooccurring substance use and mental health conditions. Renovations or replacement plans include modernizing outdated building systems, food service equipment, plumbing, and mechanical systems. Plans also include enlarged common use spaces, flexible program spaces accommodating changing program and service needs, durability features to withstand heavy facility use, technology integration, updated building security, reconfiguration and expansion of the medication suite with updated secure access capabilities, and adding onsite studio style supportive housing units.",
    ),
}

# PREC_IDENT by congressional district, from the precinct descriptions.
PRECINCTS_BY_CD = {
    "8": [
        "106", "110", "301", "302", "303", "305", "307", "310", "311", "312", "314", "315", "316",
        "317", "318", "401", "402", "404", "405", "406", "408", "410", "411", "413", "420", "421",
        "423", "424", "428", "429", "433", "501", "502", "503", "504", "505", "506", "507", "508",
        "509", "510", "511", "512", "513", "514", "515", "516", "517", "518", "520", "521", "523",
        "525", "526", "527", "530", "535", "536", "601", "602", "604", "605", "606", "607", "608",
        "609", "610", "611", "612", "613", "614", "615", "616", "621", "627", "635", "637", "705",
        "708", "710", "712", "713",
    ],
    "10": [
        "803", "815", "858", "859", "860", "862", "915", "923",
    ],
    "11": [
        "104", "105", "108", "109", "113", "114", "115", "116", "117", "118", "119", "120", "121",
        "123", "125", "126", "127", "128", "129", "130", "131", "132", "134", "135", "136", "137",
        "138", "201", "202", "203", "204", "208", "209", "213", "214", "216", "218", "219", "220",
        "221", "222", "223", "224", "225", "226", "227", "229", "233", "234", "235", "236", "237",
        "238", "240", "241", "242", "243", "244", "245", "304", "306", "309", "319", "320", "321",
        "322", "323", "324", "325", "327", "328", "329", "331", "332", "403", "415", "417", "418",
        "419", "422", "426", "427", "431", "432", "522", "528", "617", "618", "622", "623", "628",
        "629", "630", "631", "632", "633", "634", "636", "700", "701", "704", "707", "709", "711",
        "714", "718", "720", "721", "723", "726", "727", "729", "731", "732", "733", "734", "735",
        "736", "737", "738", "801", "802", "804", "805", "806", "807", "811", "812", "824", "825",
        "833", "838", "839", "841", "842", "843", "844", "845", "846", "847", "848", "849", "850",
        "851", "854", "855", "856", "857", "861", "901", "902", "903", "904", "905", "908", "909",
        "910", "911", "913", "914", "916", "917", "918", "919", "920", "921", "924", "925", "926",
        "927", "928", "929", "931", "934", "935",
    ],
}
SPLIT_PRECINCTS = {"409": ["8th CD Full", "11th CD Full"]}  # Pioneer, "CONGRESSIONAL DISTRICT: 11/8"
HERNDON_PRECINCTS = ["319", "320", "324"]  # Herndon #1, #2, #3
EXPECTED_PRECINCTS = 266


def precinct_styles():
    styles = {}
    for cd, numbers in PRECINCTS_BY_CD.items():
        for n in numbers:
            styles[n] = [f"{cd}th CD Full"]
    for n in HERNDON_PRECINCTS:
        assert styles[n] == ["11th CD Full"], n
        styles[n] = ["Herndon Full", "Herndon Town Exception"]
    for n, split in SPLIT_PRECINCTS.items():
        assert n not in styles, n
        styles[n] = split
    assert len(styles) == EXPECTED_PRECINCTS, len(styles)
    return styles


def dq(value: str, tag: str = "q") -> str:
    return f"${tag}${value}${tag}$"


def sql_text(value):
    return "null" if value is None else dq(str(value))


def sql_bool(value: bool) -> str:
    return "true" if value else "false"


def source_id(pdf: str) -> str:
    return str(uuid.uuid5(NS, pdf))


def main():
    out = sys.stdout
    out.write("-- Generated by scripts/load_fairfax_general_2026.py. Idempotent: safe to re-run.\n\n")

    for pdf, _ in STYLES.values():
        out.write(
            "insert into sources (source_id, source_url, source_type, effective_date, confidence, notes)\n"
            f"values ('{source_id(pdf)}', {sql_text(PDF_BASE + pdf)}, 'sample_ballot_pdf', '{PUBLISHED_DATE}', 1.0, "
            f"{sql_text('Fairfax County Office of Elections sample ballot, 2026 general election')})\n"
            "on conflict (source_id) do update set fetched_at = now(), effective_date = excluded.effective_date;\n\n"
        )
    calendar_source = source_id(STYLES["8th CD Full"][0])

    out.write(
        "insert into elections (election_id, name, election_type, election_date, state, jurisdiction_scope, "
        "party_scope, is_special, status, source_id)\n"
        f"values ('{ELECTION_ID}', '2026 General Election', 'general', '2026-11-03', 'VA', 'state', null, false, "
        f"'scheduled', '{calendar_source}')\n"
        "on conflict (election_id) do nothing;\n\n"
        # Virginia polls are open 6am-7pm (Code of Virginia 24.2-603); stored
        # as polls-close time like the MD calendar.
        "insert into deadlines (election_id, deadline_type, deadline_at, source_id, notes)\n"
        f"values ('{ELECTION_ID}', 'election_day', '2026-11-03 19:00 America/New_York', '{calendar_source}', "
        f"{sql_text('polls open 6am-7pm')})\n"
        "on conflict (election_id, deadline_type) do update set deadline_at = excluded.deadline_at, notes = excluded.notes;\n\n"
    )

    out.write(
        "insert into precincts (precinct_code, precinct_name, county_fips, state, geom)\n"
        f"select district_id, district_name, '{COUNTY_FIPS}', 'VA', geom from district_boundaries\n"
        "where layer_id = 'va_fairfax_precincts'\n"
        "on conflict (state, county_fips, precinct_code, effective_from) do update\n"
        "  set precinct_name = excluded.precinct_name, geom = excluded.geom;\n\n"
    )

    for key, (office_name, level, label, layer_id, district_id, scope, nonpartisan, vote_for, order,
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
            f"{sql_text(scope)}, {sql_bool(nonpartisan)}, false, true, {vote_for}, {order}, "
            f"'{source_id(next(pdf for pdf, keys in STYLES.values() if key in keys))}'\n"
            f"from offices o where o.name = {sql_text(office_name)} and o.level = {sql_text(level)}\n"
            "on conflict (election_id, office_id, coalesce(district_id, ''), contest_label) do update\n"
            "  set vote_for = excluded.vote_for, scope = excluded.scope, nonpartisan = excluded.nonpartisan,\n"
            "      order_on_ballot = excluded.order_on_ballot;\n\n"
        )
        unopposed = len(candidates) <= vote_for
        for i, (cand_name, party) in enumerate(candidates, start=1):
            out.write(
                "insert into candidates (contest_id, name, party, unopposed, ballot_order, source_id)\n"
                f"select c.contest_id, {sql_text(cand_name)}, {sql_text(party)}, {sql_bool(unopposed)}, {i}, c.source_id\n"
                "from contests c\n"
                f"where c.election_id = '{ELECTION_ID}' and c.contest_label = {sql_text(label)}\n"
                "and not exists (\n"
                "  select 1 from candidates existing\n"
                f"  where existing.contest_id = c.contest_id and existing.name = {sql_text(cand_name)}\n"
                ");\n\n"
            )

    for key, order, scope, layer_id, district_id, title, question_text in MEASURES:
        explanation_url, explanation = EXPLANATIONS[key]
        out.write(
            "insert into ballot_measures (measure_id, election_id, district_layer_id, district_id, jurisdiction_scope, "
            "title, question_text, explanation, explanation_source_url, order_on_ballot, source_id)\n"
            f"values ('{measure_id(key)}', '{ELECTION_ID}', {sql_text(layer_id)}, {sql_text(district_id)}, "
            f"'{scope}', {sql_text(title)}, {sql_text(question_text)}, {sql_text(explanation)}, "
            f"{sql_text(explanation_url)}, {order}, '{calendar_source}')\n"
            "on conflict (measure_id) do update set title = excluded.title, question_text = excluded.question_text,\n"
            "  explanation = excluded.explanation, explanation_source_url = excluded.explanation_source_url;\n\n"
        )

    rows = ",\n".join(
        f"  ('{COUNTY_FIPS}-{n}', {sql_text(style)}, {sql_text(PDF_BASE + STYLES[style][0])}, '{source_id(STYLES[style][0])}'::uuid)"
        for n, styles in sorted(precinct_styles().items()) for style in styles
    )
    out.write(
        "insert into ballot_styles (election_id, precinct_id, party, style_code, sample_ballot_url, source_id)\n"
        f"select '{ELECTION_ID}', p.precinct_id, null, v.style_code, v.url, v.source_id\n"
        f"from (values\n{rows}\n) v(precinct_code, style_code, url, source_id)\n"
        f"join precincts p on p.precinct_code = v.precinct_code and p.state = 'VA' and p.county_fips = '{COUNTY_FIPS}'\n"
        "on conflict (election_id, precinct_id, style_code) do update\n"
        "  set sample_ballot_url = excluded.sample_ballot_url, source_id = excluded.source_id;\n\n"
    )

    links = ",\n".join(
        f"  ({sql_text(style)}, {sql_text(CONTESTS[key][2])})" for style, (_, keys) in STYLES.items() for key in keys
    )
    out.write(
        "insert into ballot_style_contests (ballot_style_id, contest_id)\n"
        "select bs.ballot_style_id, c.contest_id\n"
        f"from (values\n{links}\n) v(style_code, contest_label)\n"
        f"join ballot_styles bs on bs.election_id = '{ELECTION_ID}' and bs.style_code = v.style_code\n"
        f"join contests c on c.election_id = '{ELECTION_ID}' and c.contest_label = v.contest_label\n"
        "on conflict (ballot_style_id, contest_id) do nothing;\n\n"
        "insert into ballot_style_measures (ballot_style_id, measure_id)\n"
        "select bs.ballot_style_id, m.measure_id\n"
        f"from ballot_styles bs join ballot_measures m on m.election_id = bs.election_id\n"
        f"where bs.election_id = '{ELECTION_ID}'\n"
        "on conflict (ballot_style_id, measure_id) do nothing;\n\n"
    )

    expected_styles = sum(len(s) for s in precinct_styles().values())
    out.write(
        "do $$ begin\n"
        f"  if (select count(*) from ballot_styles where election_id = '{ELECTION_ID}') <> {expected_styles} then\n"
        f"    raise exception 'expected {expected_styles} Fairfax ballot styles: a precinct code did not match';\n"
        "  end if;\n"
        "end $$;\n"
    )

    print("Done.", file=sys.stderr)


if __name__ == "__main__":
    main()

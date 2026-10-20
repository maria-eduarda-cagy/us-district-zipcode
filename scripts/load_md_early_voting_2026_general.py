"""Loads every official Maryland early voting center for the 2026 general
election (all 24 counties) into polling_locations, from the MSBE PDF:
https://elections.maryland.gov/elections/2026/2026_Early_Voting_Centers-GG-EN.pdf

Parses the PDF text (needs poppler's `pdftotext` on PATH): each county
section is "<County> (<N> centers)" followed by name / street / "City, MD
zip" blocks. Fails loudly (exit 1, no SQL) unless every county's block count
matches both its header and the PDF's own "Total Number of Early Voting
Centers" table.

Geocodes with the same Census -> ArcGIS chain as the primary loader. The
generated SQL ends with a check that every point falls inside its own
county's polygon (legacy `county` table), so a wrong geocode can't slip in.

Usage:
    python3 scripts/load_md_early_voting_2026_general.py > out.sql
"""
import json
import os
import re
import subprocess
import sys
import tempfile
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from load_montgomery_early_voting_2026_primary import dq, geocode, sql_text  # noqa: E402

SOURCE_URL = "https://elections.maryland.gov/elections/2026/2026_Early_Voting_Centers-GG-EN.pdf"
SOURCE_ID = "cccccccc-cccc-cccc-cccc-cccccccccccc"
GENERAL_ELECTION_ID = "55555555-5555-5555-5555-555555555555"
START_DATE = "2026-10-22"
END_DATE = "2026-10-29"
HOURS = "7:00 AM - 8:00 PM"

COUNTY_FIPS = {
    "Allegany County": "24001",
    "Anne Arundel County": "24003",
    "Baltimore City": "24510",
    "Baltimore County": "24005",
    "Calvert County": "24009",
    "Caroline County": "24011",
    "Carroll County": "24013",
    "Cecil County": "24015",
    "Charles County": "24017",
    "Dorchester County": "24019",
    "Frederick County": "24021",
    "Garrett County": "24023",
    "Harford County": "24025",
    "Howard County": "24027",
    "Kent County": "24029",
    "Montgomery County": "24031",
    "Prince George's County": "24033",
    "Queen Anne's County": "24035",
    "Saint Mary's County": "24037",
    "Somerset County": "24039",
    "Talbot County": "24041",
    "Washington County": "24043",
    "Wicomico County": "24045",
    "Worcester County": "24047",
}

COUNTY_HEADER = re.compile(r"^(.+?) \((\d+) centers?\)$")
CITY_LINE = re.compile(r"^(.+?), (?:MD |Maryland )?(\d{5})$")  # "MD", "Maryland" and omitted all occur
TOTALS_ROW = re.compile(r"^([A-Z][A-Z .'`]+?) [\d,]+ (\d+) (\d+) (\d+)$")


def normalize(text: str) -> str:
    # Match the names already stored by the primary loader ("-" and "'").
    return text.replace("–", "-").replace("’", "'").replace("“", '"').replace("”", '"').strip()


def fetch_pdf_text() -> str:
    req = urllib.request.Request(SOURCE_URL, headers={"User-Agent": "us-district-zipcode-loader/1.0"})
    with urllib.request.urlopen(req, timeout=120) as resp, tempfile.NamedTemporaryFile(suffix=".pdf") as tmp:
        tmp.write(resp.read())
        tmp.flush()
        return subprocess.run(["pdftotext", "-raw", tmp.name, "-"], capture_output=True, text=True, check=True).stdout


def parse(text: str):
    lines = [normalize(line) for line in text.splitlines()]
    lines = [line for line in lines if line and not re.match(r"^Page \d+$", line)]

    start = next(i for i, line in enumerate(lines) if COUNTY_HEADER.match(line))
    end = next(i for i, line in enumerate(lines) if "Determination of Early Voting Centers" in line)

    counties = {}  # name -> (declared_count, [(name, street, city, zip5)])
    current = None
    block = []
    for line in lines[start:end]:
        header = COUNTY_HEADER.match(line)
        if header:
            current = header.group(1)
            counties[current] = (int(header.group(2)), [])
            block = []
            continue
        block.append(line)
        city = CITY_LINE.match(line)
        if city:
            if len(block) < 3:
                raise ValueError(f"{current}: malformed block {block}")
            counties[current][1].append((block[0], " ".join(block[1:-1]), city.group(1), city.group(2)))
            block = []
        if current and block and len(block) > 4:
            raise ValueError(f"{current}: unterminated block {block}")

    totals = {}
    for line in lines[end:]:
        row = TOTALS_ROW.match(line)
        if row:
            totals[row.group(1).replace("`", "'").strip()] = int(row.group(4))
    return counties, totals


def validate(counties, totals):
    errors = []
    if set(counties) != set(COUNTY_FIPS):
        errors.append(f"county names differ: {sorted(set(counties) ^ set(COUNTY_FIPS))}")
    for county, (declared, centers) in counties.items():
        # The table drops " COUNTY" except where it disambiguates (BALTIMORE COUNTY vs BALTIMORE CITY).
        table_total = totals.get(county.upper(), totals.get(county.upper().replace(" COUNTY", "")))
        if len(centers) != declared:
            errors.append(f"{county}: header says {declared}, parsed {len(centers)}")
        if table_total != declared:
            errors.append(f"{county}: header says {declared}, totals table says {table_total}")
    return errors


def main():
    counties, totals = parse(fetch_pdf_text())
    errors = validate(counties, totals)
    if errors:
        for e in errors:
            print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
    total = sum(len(centers) for _, centers in counties.values())
    print(f"Parsed {total} centers in {len(counties)} counties; all counts match the PDF.", file=sys.stderr)

    out = sys.stdout
    out.write("-- Generated by scripts/load_md_early_voting_2026_general.py. Idempotent: safe to re-run.\n\n")
    out.write(
        "insert into sources (source_id, source_url, source_type, effective_date, confidence, notes)\n"
        f"values ('{SOURCE_ID}', {sql_text(SOURCE_URL)}, {sql_text('early_voting_centers_pdf')}, "
        f"'2026-08-03', 1.0, {sql_text('MSBE early voting centers, 2026 general election, all counties')})\n"
        "on conflict (source_id) do update set fetched_at = now(), effective_date = excluded.effective_date;\n\n"
    )

    for county, (_, centers) in sorted(counties.items()):
        fips = COUNTY_FIPS[county]
        for name, street, city, zip5 in centers:
            # Parenthetical directions / room suffixes confuse the geocoders.
            geocode_street = re.split(r" \(| - ", street)[0]
            lat, lon = geocode(geocode_street, city, zip5)
            print(f"{county}: {name}: {lat}, {lon}", file=sys.stderr)
            if lat is None:
                print(f"ERROR: could not geocode {name}, {street}, {city}", file=sys.stderr)
                sys.exit(1)
            address_json = json.dumps({"street": street, "city": city, "state": "MD", "zip5": zip5})
            out.write(
                "insert into polling_locations (election_id, location_type, name, address, geom, hours, "
                "start_date, end_date, county_fips, source_id)\n"
                f"select '{GENERAL_ELECTION_ID}', 'early_vote', {sql_text(name)}, {dq(address_json, 'j')}::jsonb, "
                f"st_setsrid(st_makepoint({lon}, {lat}), 4326), {sql_text(HOURS)}, '{START_DATE}', '{END_DATE}', "
                f"'{fips}', '{SOURCE_ID}'\n"
                "where not exists (\n"
                "  select 1 from polling_locations existing\n"
                f"  where existing.election_id = '{GENERAL_ELECTION_ID}' and existing.name = {sql_text(name)}\n"
                f"  and existing.county_fips = '{fips}'\n"
                ");\n\n"
            )

    out.write(
        "do $check$\n"
        "declare outside text;\n"
        "begin\n"
        f"  if (select count(*) from polling_locations where election_id = '{GENERAL_ELECTION_ID}'\n"
        f"      and location_type = 'early_vote') <> {total} then\n"
        f"    raise exception 'expected {total} general early voting centers';\n"
        "  end if;\n"
        "  select string_agg(p.name || ' (' || p.county_fips || ')', '; ') into outside\n"
        "  from polling_locations p join county c on c.id = p.county_fips\n"
        f"  where p.election_id = '{GENERAL_ELECTION_ID}' and not st_intersects(c.geom, p.geom);\n"
        "  if outside is not null then\n"
        "    raise exception 'geocoded outside their county: %', outside;\n"
        "  end if;\n"
        "end $check$;\n"
    )
    print("Done.", file=sys.stderr)


if __name__ == "__main__":
    main()

"""Parses a Maryland State Board of Elections certified general election
ballot PDF (https://elections.maryland.gov/elections/2026/general_ballots/
<County>.pdf, one per county) into ballot styles: style code, precinct(s),
contests with candidates and parties, and ballot questions -- all as printed.

Works from `pdftohtml -xml` (text runs with page coordinates and fonts). The
layout is the same across counties, give or take a few points:

- A style starts on a page whose header reads "BS <n>" (+ "Page 1 of <N>"
  when it has more than one sheet) and carries the precinct code(s)
  ("008-006"); following pages belong to the same style until the next
  "Page 1" (each sheet is printed front and back).
- Contest columns are found from their "Vote for ..." / "Vote Yes or No" /
  "Question <n>" lines. A contest's title is the bold lines at the column
  edge above "Vote for"; candidates are the 18pt bold names indented under
  it, each followed by its party in a smaller font ("Democratic", then
  " /Demócrata" in a separate run on bilingual ballots). A name can wrap to
  two lines; running mates are joined by an "and" line.
- Some counties also print invisible 1pt white text (screen-reader labels)
  duplicating the visible text; it is ignored.

The output is literal ballot text; mapping titles to offices/districts is the
loader's job.

Usage:
    python3 scripts/md_general_ballot_parser.py Montgomery.pdf > montgomery.json
"""
import html
import json
import re
import subprocess
import sys
from dataclasses import asdict, dataclass, field

HEADER_BOTTOM = 270  # the page header sits above this on a style's front pages...
HEADER_LEFT = (150, 300)  # ...in the title block, or (right side) in 30pt type
FOOTER_TOP = 1728  # "Vote All Sides" / "End of Ballot"
CANDIDATE_INDENT = 23
NAME_SIZE = 17  # candidate names and titles are 18pt; party / "and" / write-in lines are 15-16pt
# "Non-Partisan Contest / Candidates in this contest may or may not be
# affiliated with any political party", wrapped differently by county.
NONPARTISAN = re.compile(r"Non-Partisan Contest|^(be )?affiliated with any political party$|^Candidates in this contest")
VOTE_FOR = re.compile(r"^Vote (?:for (?:up to )?(\d+)|Yes or No)$")
QUESTION = re.compile(r"^Question [\w-]+$")
STYLE_HEADER = re.compile(r"\bBS (\d+[A-Z]?)\b")
PRECINCT = re.compile(r"(?<![\d-])(\d{3}-\d{3})(?![\d-])")


@dataclass
class Run:
    top: int
    left: int
    text: str
    size: int
    bold: bool


@dataclass
class Candidate:
    name: str
    party: str | None


@dataclass
class Contest:
    title: list[str]
    vote_for: int
    nonpartisan: bool
    retention: bool
    notes: list[str] = field(default_factory=list)  # e.g. "No More than 1 per County", "For Continuance in Office"
    candidates: list[Candidate] = field(default_factory=list)


@dataclass
class Measure:
    header: list[str]
    paragraphs: list[str]
    options: list[str]


@dataclass
class Style:
    style_code: str
    precincts: list[str]
    first_page: int
    contests: list[Contest] = field(default_factory=list)
    measures: list[Measure] = field(default_factory=list)


def read_pages(pdf_path: str):
    xml = subprocess.run(
        ["pdftohtml", "-xml", "-i", "-q", "-stdout", pdf_path], capture_output=True, text=True, check=True
    ).stdout
    fonts = {}
    for m in re.finditer(r'<fontspec id="(\d+)" size="(-?\d+)" family="([^"]+)" color="([^"]+)"', xml):
        fonts[m.group(1)] = (int(m.group(2)), "Bold" in m.group(3), m.group(4).lower())
    for m in re.finditer(r'<page number="(\d+)"[^>]*>(.*?)</page>', xml, re.S):
        runs = []
        for t in re.finditer(r'<text top="(-?\d+)" left="(-?\d+)" width="\d+" height="\d+" font="(\d+)">(.*?)</text>',
                             m.group(2), re.S):
            text = html.unescape(re.sub(r"<[^>]+>", "", t.group(4))).strip()
            size, bold, color = fonts[t.group(3)]
            if not text or (size <= 2 and color == "#ffffff"):  # screen-reader duplicate
                continue
            runs.append(Run(int(t.group(1)), int(t.group(2)), text, size, bold))
        yield int(m.group(1)), runs


def is_vote_line(r: Run) -> bool:
    # 21pt; Kent also prints an 18pt "Vote for up to 3" under the title.
    return r.bold and r.size >= 20 and bool(VOTE_FOR.match(r.text))


def near(a: int, b: int, tol: int = 4) -> bool:
    return abs(a - b) <= tol


def is_title_line(r: Run, x: int) -> bool:
    return r.bold and near(r.left, x, 8) and r.size >= NAME_SIZE


def split_columns(runs: list[Run]) -> dict[int, list[Run]]:
    starts: list[int] = []
    for r in runs:
        if (is_vote_line(r) or (r.bold and QUESTION.match(r.text))) and not any(near(r.left, s, 8) for s in starts):
            starts.append(r.left)
    columns: dict[int, list[Run]] = {s: [] for s in sorted(starts)}
    for r in runs:
        owner = max((s for s in columns if s <= r.left + 8), default=None)
        if owner is not None:
            columns[owner].append(r)
    return {s: sorted(rs, key=lambda r: (r.top, r.left)) for s, rs in columns.items()}


def parse_contest(col: list[Run], i: int, x: int) -> tuple[Contest, int]:
    """col[i] is the "Vote for" line. Returns the contest and the index after it."""
    title = []
    prev_top = col[i].top
    for r in reversed(col[:i]):
        # Stop at the previous contest's candidates / write-in lines, or at a
        # gap wider than within a title (e.g. the voting instructions above
        # the first contest of a column).
        if r.left > x + 10 or is_vote_line(r) or QUESTION.match(r.text) or prev_top - r.top > 50:
            break
        if r.bold and not VOTE_FOR.match(r.text):
            title.insert(0, r.text)
            prev_top = r.top
    nonpartisan = any(NONPARTISAN.search(line) for line in title)
    title = [line for line in title if not NONPARTISAN.search(line)]
    m = VOTE_FOR.match(col[i].text)
    retention = m.group(1) is None
    contest = Contest(title=title, vote_for=1 if retention else int(m.group(1)), nonpartisan=nonpartisan,
                      retention=retention)
    if retention:
        # "Judge, Appellate Court of Maryland At Large" / "Dan Friedman" / Vote Yes or No
        contest.candidates.append(Candidate(name=title[-1], party=None))
        contest.title = title[:-1]

    # Candidates are indented ~18-23pt from the title, depending on the county.
    cand_x = next((r.left for r in col[i + 1:] if r.bold and r.size >= NAME_SIZE and x + 10 < r.left < x + 40),
                  x + CANDIDATE_INDENT)
    j = i + 1
    joining = None  # "wrap" while a name may continue on the next line, "and" after a running-mate line
    last_name_top = -1000
    seen_write_in = False  # a write-in-only contest has no candidates to end the notes
    while j < len(col):
        r = col[j]
        # A bold line back at the column edge is a note under "Vote for"
        # until the first candidate; after that, the next contest's title.
        if is_vote_line(r) or (r.bold and QUESTION.match(r.text)):
            break
        if is_title_line(r, x):
            if seen_write_in or (contest.candidates and not (retention and len(contest.candidates) == 1
                                                             and not contest.notes)):
                break
            contest.notes.append(r.text)
            j += 1
            continue
        if not retention and r.left >= cand_x - 4:
            if r.text.startswith("or write-in"):
                joining = None
                seen_write_in = True
            elif r.text == "and":
                joining = "and"
            elif r.bold and r.size >= NAME_SIZE and near(r.left, cand_x):
                if joining == "wrap" and r.top - last_name_top > 22:  # next candidate, not a wrapped name
                    joining = None
                last_name_top = r.top
                if joining and contest.candidates:
                    contest.candidates[-1].name += (" / " if joining == "and" else " ") + r.text
                else:
                    contest.candidates.append(Candidate(name=r.text, party=None))
                joining = "wrap"
            elif r.size < NAME_SIZE and near(r.left, cand_x) and contest.candidates \
                    and contest.candidates[-1].party is None and joining == "wrap":
                contest.candidates[-1].party = r.text
                joining = None
        j += 1
    return contest, j


def parse_measure(col: list[Run], i: int, x: int) -> tuple[Measure, int]:
    """col[i] is the "Question <n>" line."""
    lines = [col[i]]
    options = []
    j = i + 1
    while j < len(col):
        r = col[j]
        if is_vote_line(r) or (r.bold and QUESTION.match(r.text)):
            break
        if r.bold and x + 10 < r.left < x + 40:  # response options, indented like candidates
            options.append(r.text)
        elif options and is_title_line(r, x):
            break
        elif near(r.left, x, 8) and r.size >= NAME_SIZE and not options:  # body is bold in some counties, not all
            lines.append(r)
        j += 1
    # Bilingual ballots (Montgomery, Prince George's) print the English in
    # bold and the Spanish translation ("Pregunta 1 ...") in regular type.
    if any(r.text.startswith("Pregunta") for r in lines):
        lines = [r for r in lines if r.bold]
    # Header: the bold lines right under "Question <n>"; the body follows.
    h = 1
    while h < len(lines) and lines[h].bold and lines[h].top - lines[h - 1].top <= 30:
        h += 1
    paragraphs = [re.sub(r"\s+", " ", " ".join(r.text for r in b)).strip() for b in paragraph_blocks(lines[h:])]
    return Measure(header=[r.text for r in lines[:h]], paragraphs=paragraphs, options=options), j


def paragraph_blocks(lines: list[Run]) -> list[list[Run]]:
    """Paragraphs are separated by a gap larger than the normal line spacing."""
    blocks: list[list[Run]] = []
    for r in lines:
        if blocks and r.top - blocks[-1][-1].top <= 22:
            blocks[-1].append(r)
        else:
            blocks.append([r])
    return blocks


def parse_page(runs: list[Run], style: Style):
    for x, col in split_columns(runs).items():
        i = 0
        while i < len(col):
            r = col[i]
            if is_vote_line(r):
                contest, i = parse_contest(col, i, x)
                style.contests.append(contest)
            elif r.bold and QUESTION.match(r.text):
                measure, i = parse_measure(col, i, x)
                style.measures.append(measure)
            else:
                i += 1


def is_header(r: Run) -> bool:
    return r.top < HEADER_BOTTOM and (HEADER_LEFT[0] <= r.left < HEADER_LEFT[1] or r.size >= 30)


def parse_pdf(pdf_path: str) -> list[Style]:
    styles: list[Style] = []
    for number, runs in read_pages(pdf_path):
        head = [r for r in runs if is_header(r)]
        head_text = " ".join(r.text for r in head)
        if "Official Ballot" in head_text and (code := STYLE_HEADER.search(head_text)):
            page_of = re.search(r"Page (\d+) of (\d+)", head_text)
            if page_of is None or page_of.group(1) == "1":
                styles.append(Style(style_code=f"BS {code.group(1)}",
                                    precincts=sorted(set(PRECINCT.findall(head_text))), first_page=number))
            runs = [r for r in runs if not is_header(r)]
        if styles:
            parse_page([r for r in runs if r.top < FOOTER_TOP], styles[-1])
    return styles


def main():
    styles = parse_pdf(sys.argv[1])
    json.dump([asdict(s) for s in styles], sys.stdout, indent=1, ensure_ascii=False)
    print(f"{len(styles)} styles", file=sys.stderr)


if __name__ == "__main__":
    main()

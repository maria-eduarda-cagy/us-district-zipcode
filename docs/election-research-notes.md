# Research: election calendar and data availability (Maryland 2026)

Researched 2026-07-02 via web search (official sources). See [data-sources.md](data-sources.md) for full URLs.

## Confirmed dates — 2026 cycle, Maryland

| Event | Date |
|---|---|
| Primary (Gubernatorial Primary Election) | 2026-06-23 |
| Primary early voting | 2026-06-11 to 2026-06-18 |
| **Certification of primary ballot content/arrangement** | 2026-04-14 (legal basis: EL § 9-207(a)(2)) |
| General election | 2026-11-03 |
| General early voting | 2026-10-22 to 2026-10-29 |
| Non-principal party candidate filing deadline for the general (Deadline #1) | 2026-07-06 |

## Status as of 2026-07-02 (today)

- The **primary has already happened** (June 23) and its ballot is already certified, real public data — this is what we used in task 3.
- The **general (Nov 3) has no certified ballot yet**. The non-principal party candidate filing deadline only closes on 2026-07-06 — meaning the candidate list hadn't even closed as of this research.
- Certification of the general ballot normally happens **after** filing closes — based on MD's historical election calendar pattern, this tends to fall between August and September, but that specific date **was not confirmed** in this research (it's an inference based on prior cycles, not a verified fact). Before using that date for anything, re-check the official source.

## Practical implication

**It is not possible today to build a real, certified ballot for the November 2026 general election.** Populating `elections`/`ballot_styles`/`contests`/`candidates` for the general right now would necessarily be fabricated or provisional data (candidates not yet confirmed) — the same mistake that motivated removing the fictitious `ballot_measures` from the old `main.py`.

Recommendation: task 4 (populate `elections`/`deadlines`) should create the **general election row** (date, type, already-known deadlines) so the calendar works, but **without** associated ballot_styles/contests/candidates until the MSBE publishes the certified ballot. When that happens, repeat the task 3 process (locate certified PDF → extract text → transcribe contests/candidates).

## Recommended update cadence (from the original research report)

| Data | Suggested frequency |
|---|---|
| Calendar and deadlines | Daily in an election year close to the window; weekly outside it |
| Candidate list | Daily during the filing window; 2x/day close to ballot certification |
| Polling locations / early voting / drop boxes | Daily in the 8 weeks before the election |
| Certified ballot styles | Check when the MSBE announces certification; heavy checking in the final weeks |
| District / precinct boundaries | Event-driven (redistricting) + monthly verification |

## Sources used in this research

- [2026 Gubernatorial Election - Maryland State Board of Elections](https://elections.maryland.gov/elections/2026/index.html)
- [Candidacy Introduction - Maryland State Board of Elections](https://elections.maryland.gov/candidacy/index.html)
- [Official Voter Guide and Sample Ballot - Montgomery County](https://mcg.montgomerycountymd.gov/elections/VotingServices/SampleBallotVoterGuide.html)
- [Certified Official Ballot, Montgomery County, Primary 2026-06-23 (PDF)](https://elections.maryland.gov/elections/2026/primary_ballots/Montgomery.pdf)

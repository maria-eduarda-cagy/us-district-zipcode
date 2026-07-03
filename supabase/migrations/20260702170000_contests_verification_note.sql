-- Some contests carry a known, unresolved data-quality conflict between the
-- certified ballot PDF and other official sources (e.g. Montgomery County's
-- own precinct-to-district crosswalk and live GIS layer disagreeing with the
-- ballot's printed district for the same office/precinct). Rather than
-- silently pick one source or hide the discrepancy, flag it explicitly so
-- the frontend can show a visible caveat instead of presenting the contest
-- as fully verified.

alter table contests add column if not exists verification_note text;

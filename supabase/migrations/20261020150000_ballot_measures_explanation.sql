-- Official plain-language explanation of a ballot measure, when it is
-- published separately from the ballot (e.g. Virginia ELECT's "Present law /
-- Proposed law" explanations, Fairfax County's bond statements). Kept apart
-- from impact_yes/impact_no, which hold the FOR/AGAINST text printed on the
-- ballot itself (Maryland).
alter table ballot_measures
  add column if not exists explanation text,
  add column if not exists explanation_source_url text;

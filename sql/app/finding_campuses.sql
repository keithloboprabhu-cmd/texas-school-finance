-- New campuses (first NCES appearance 2016-17 or later) still open, in school districts (not charters).
-- Same definition as the Growth & Construction headline.
SELECT count(*) AS new_open FROM mart_campuses WHERE is_new AND is_open AND NOT is_charter;

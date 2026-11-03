-- New campuses (first NCES appearance 2016-17 or later) still open, in ISDs
SELECT count(*) AS new_open FROM mart_campuses WHERE is_new AND is_open AND in_analysis;

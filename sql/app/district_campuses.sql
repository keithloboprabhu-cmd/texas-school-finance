-- Open campuses of $cdn (NCES EDGE), with first year listed
SELECT school_name, first_year, is_new, lat, lon FROM mart_campuses WHERE cdn = $cdn AND is_open ORDER BY first_year DESC, school_name;

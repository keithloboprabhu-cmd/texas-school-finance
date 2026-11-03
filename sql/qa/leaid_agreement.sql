-- NCES CCD and TEA AskTED must agree on every district's NCES LEAID.
SELECT cdn, district_name FROM dim_district WHERE leaid_conflict;

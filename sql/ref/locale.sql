-- NCES urban-centric locale codes. Category/subcategory structure from the EDGE LEA geocode
-- field names (PCT_CITY11..PCTRURAL43) and NCES locale documentation:
-- https://nces.ed.gov/programs/edge/Geographic/LocaleBoundaries
CREATE OR REPLACE TABLE ref_locale AS
SELECT * FROM (VALUES
  ('11', 'City', 'City: Large'),       ('12', 'City', 'City: Midsize'),     ('13', 'City', 'City: Small'),
  ('21', 'Suburb', 'Suburb: Large'),   ('22', 'Suburb', 'Suburb: Midsize'), ('23', 'Suburb', 'Suburb: Small'),
  ('31', 'Town', 'Town: Fringe'),      ('32', 'Town', 'Town: Distant'),     ('33', 'Town', 'Town: Remote'),
  ('41', 'Rural', 'Rural: Fringe'),    ('42', 'Rural', 'Rural: Distant'),   ('43', 'Rural', 'Rural: Remote')
) AS t(locale_code, locale, locale_detail);

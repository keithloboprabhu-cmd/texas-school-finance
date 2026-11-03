-- Enrollment growth and capital intensity per current district.
-- Cost proxies (labelled as proxies everywhere): Texas has no statewide dataset of school
-- construction cost per square foot, so none is shown.
CREATE OR REPLACE TABLE mart_growth_capital AS
WITH y AS (SELECT max(year) AS y FROM mart_district_year),
e AS (
  SELECT cdn,
    max(enrollment) FILTER (WHERE year = (SELECT y FROM y))      AS enroll_now,
    max(enrollment) FILTER (WHERE year = (SELECT y FROM y) - 5)  AS enroll_5y_ago,
    max(enrollment) FILTER (WHERE year = (SELECT y FROM y) - 10) AS enroll_10y_ago,
    sum(capital * real_factor) FILTER (WHERE year > (SELECT y FROM y) - 5)            AS capital_5y_real,
    avg(capital_per_student_real) FILTER (WHERE year > (SELECT y FROM y) - 5)         AS capital_per_student_5y_avg
  FROM mart_district_year WHERE is_current GROUP BY cdn
), c AS (
  SELECT cdn, count(*) FILTER (WHERE is_new) AS new_campuses_since_2016_17,
         count(*) FILTER (WHERE is_new AND first_year > (SELECT y FROM y) - 5) AS new_campuses_5y
  FROM mart_campuses WHERE cdn IS NOT NULL GROUP BY cdn
)
SELECT d.cdn, d.district_name, d.county, d.esc_region, d.locale, d.is_metro, d.cbsa_name, d.lat, d.lon,
       e.enroll_now, e.enroll_5y_ago, e.enroll_10y_ago,
       e.enroll_now / nullif(e.enroll_5y_ago, 0) - 1  AS growth_5y,
       e.enroll_now / nullif(e.enroll_10y_ago, 0) - 1 AS growth_10y,
       e.enroll_now - e.enroll_5y_ago                 AS students_added_5y,
       e.capital_5y_real, e.capital_per_student_5y_avg,
       coalesce(c.new_campuses_since_2016_17, 0) AS new_campuses_since_2016_17,
       coalesce(c.new_campuses_5y, 0) AS new_campuses_5y,
       -- PROXY: real capital spending over 5 years per student added over the same 5 years
       CASE WHEN e.enroll_now - e.enroll_5y_ago >= 50
            THEN e.capital_5y_real / (e.enroll_now - e.enroll_5y_ago) END AS proxy_capital_per_new_student,
       -- PROXY: real capital spending over 5 years per campus opened in those 5 years
       CASE WHEN c.new_campuses_5y > 0 THEN e.capital_5y_real / c.new_campuses_5y END AS proxy_capital_per_new_campus,
       e.enroll_now < 500 AS small_district, d.enrollment_caution, d.virtual_share
FROM mart_districts d JOIN e USING (cdn) LEFT JOIN c USING (cdn);

-- Coefficients of the simple, controlled (WLS, HC1) and Huber robust models, latest year
SELECT model, term, coef, std_err, ci_lo, ci_hi, p_value, n, r2, year FROM mart_model_latest ORDER BY model, term;

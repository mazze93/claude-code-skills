-- schema: list tables and views
SELECT type, name FROM sqlite_master WHERE type IN ('table','view') ORDER BY type, name;

-- schema: column definitions for tool_calls, failures, sessions
SELECT name, sql FROM sqlite_master WHERE name IN ('tool_calls','failures','sessions','v_tool_reliability','v_outcome_coverage','v_failures_by_layer_detection');

-- sessions in the db
SELECT * FROM sessions;

-- outcome distribution and record source
SELECT outcome, record_source, COUNT(*) AS n FROM tool_calls GROUP BY outcome, record_source ORDER BY n DESC;

-- Q1: calls that failed without the tool flagging an error (output-scan)
SELECT call_id, exchange, seq, tool_short, description, error_signature, error_excerpt, failure_id, outcome_source FROM tool_calls WHERE outcome = 'error_unflagged' ORDER BY call_id;

-- Q1 context: flagged errors for comparison
SELECT call_id, tool_short, description, substr(error_excerpt,1,150) FROM tool_calls WHERE outcome='error';

-- Q1 context: attested failures (no recorded result; failure inferred from another source)
SELECT call_id, tool_short, description, outcome_source, failure_id FROM tool_calls WHERE outcome='attested_fail' ORDER BY call_id;

-- all failures (full log)
SELECT failure_id, exchange, call_id, link_basis, layer, class, detection, detected_by, detected_in, exchanges_to_detect, caught, severity, status, summary FROM failures ORDER BY failure_id;

-- Q2: escaped to delivery, by layer (analysis.md)
SELECT layer, COUNT(*) AS escaped, ROUND(AVG(severity), 2) AS avg_severity, SUM(severity) AS severity_points FROM failures WHERE caught = 'after-delivery' GROUP BY layer ORDER BY escaped DESC;

-- Q2: escape rate per layer (escaped / total in layer)
SELECT layer, COUNT(*) AS total, SUM(caught='after-delivery') AS escaped, ROUND(100.0*SUM(caught='after-delivery')/COUNT(*),1) AS pct_escaped FROM failures GROUP BY layer ORDER BY escaped DESC, total DESC;

-- Q2: escaped failures, row by row
SELECT failure_id, layer, class, severity, detection, detected_by, exchange, detected_in, exchanges_to_detect, status FROM failures WHERE caught='after-delivery' ORDER BY layer, failure_id;

-- Q2: escaped by class
SELECT class, COUNT(*) FROM failures WHERE caught='after-delivery' GROUP BY class ORDER BY 2 DESC;

-- Q2 check: caught values and who detected the escapes
SELECT caught, detected_by, COUNT(*) FROM failures GROUP BY caught, detected_by;

-- Caveat: how much of the record can be checked (analysis.md)
SELECT session_id, COUNT(*) AS calls, SUM(outcome != 'unrecorded') AS with_outcome, ROUND(100.0 * SUM(outcome != 'unrecorded') / COUNT(*), 1) AS pct_with_outcome, SUM(record_source IN ('transcript','hook')) AS calls_with_results, SUM(record_source IN ('export','manual')) AS calls_without_results FROM tool_calls GROUP BY session_id;

-- Caveat: unflagged-failure scan only runs where results exist -- results-bearing calls by tool
SELECT tool_short, COUNT(*) AS calls_with_results, SUM(outcome='error_unflagged') AS unflagged, SUM(outcome='error') AS flagged FROM tool_calls WHERE record_source='transcript' GROUP BY tool_short ORDER BY calls_with_results DESC;

-- Caveat: which exchanges have recorded results
SELECT exchange, record_source, COUNT(*) FROM tool_calls GROUP BY exchange, record_source ORDER BY exchange;

-- Check: does any failure point at E14-007
SELECT failure_id, call_id, summary FROM failures WHERE call_id='E14-007' OR summary LIKE '%pages%';


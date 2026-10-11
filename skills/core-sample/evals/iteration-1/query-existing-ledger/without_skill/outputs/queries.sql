-- Every query run against core-sample.sqlite (opened read-only: file:...?mode=ro), in order.
-- Runner: python3 sqlite3, uri=True. No writes were issued.

SELECT type, name, sql FROM sqlite_master ORDER BY type, name;

SELECT * FROM sessions;

SELECT session_id, outcome, outcome_source, record_source, COUNT(*) FROM tool_calls GROUP BY 1,2,3,4 ORDER BY 1,2;

SELECT COUNT(*) FROM tool_calls;

SELECT COUNT(*) FROM failures;

SELECT COUNT(*) FROM exchanges;

SELECT DISTINCT layer, class, detection, detected_by, caught FROM failures ORDER BY 1,2;

SELECT call_id, exchange, seq, tool_short, family, outcome, outcome_source, record_source, error_signature, substr(error_excerpt,1,200), failure_id, substr(description,1,120) FROM tool_calls WHERE outcome IN ('error','error_unflagged','attested_fail') ORDER BY exchange, seq;

SELECT DISTINCT error_signature FROM tool_calls;

SELECT f.failure_id, f.exchange, f.call_id, f.link_basis, f.layer, f.class, f.detection, f.detected_by, f.detected_in, f.exchanges_to_detect, f.caught, f.severity, f.status, t.outcome AS call_outcome, f.summary FROM failures f LEFT JOIN tool_calls t ON t.session_id=f.session_id AND t.call_id=f.call_id ORDER BY f.failure_id;

SELECT layer, COUNT(*) AS total, SUM(caught='after-delivery') AS after_delivery, SUM(CASE WHEN caught='after-delivery' THEN severity ELSE 0 END) AS sev_after, SUM(CASE WHEN caught='after-delivery' THEN exchanges_to_detect ELSE 0 END) AS exch_to_detect_after FROM failures GROUP BY layer ORDER BY after_delivery DESC, total DESC;

SELECT caught, detected_by, COUNT(*) FROM failures GROUP BY 1,2;

SELECT detection, COUNT(*) FROM failures WHERE caught='after-delivery' GROUP BY 1 ORDER BY 2 DESC;

SELECT t.call_id, t.failure_id, f.call_id FROM tool_calls t LEFT JOIN failures f ON f.session_id=t.session_id AND f.failure_id=t.failure_id WHERE t.failure_id IS NOT NULL AND t.failure_id<>'' AND (f.call_id IS NULL OR f.call_id<>t.call_id);

SELECT COUNT(*) FROM tool_calls WHERE failure_id IS NOT NULL AND failure_id<>'';

SELECT exchange, COUNT(*) AS calls, SUM(outcome='unrecorded') AS unrecorded, SUM(outcome='ok') AS ok FROM tool_calls GROUP BY exchange ORDER BY exchange;

SELECT exchange, ordinal, initiator, kind, response_kind, substr(prompt,1,100) FROM exchanges ORDER BY ordinal;


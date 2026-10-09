# Questions worth asking a core-sample database

Every table carries `session_id`, so each query below works for one session
(add `WHERE session_id = '…'`) or across all of them.

## How much of the record can anyone check?
```sql
SELECT session_id,
       ROUND(100.0 * SUM(outcome != 'unrecorded') / COUNT(*), 1) AS pct_checkable,
       SUM(record_source IN ('export','manual')) AS calls_without_results
FROM tool_calls GROUP BY session_id;
```
A falling percentage means sessions are being compacted without the hook.

## Which failures did the tool's own error flag miss?
```sql
SELECT call_id, tool_short, error_signature, error_excerpt
FROM tool_calls WHERE outcome = 'error_unflagged';
```
These are usually a pipe (`| tail`, `| head`) hiding an exit code. If the
same tool keeps showing up here, change the habit rather than the scanner.

## What escapes to delivery, and from which layer?
```sql
SELECT layer, COUNT(*) AS escaped, ROUND(AVG(severity), 2) AS avg_severity
FROM failures WHERE caught = 'after-delivery' GROUP BY layer ORDER BY escaped DESC;
```

## What actually catches failures?
```sql
SELECT detection, COUNT(*) AS caught, SUM(severity) AS severity_points
FROM failures GROUP BY detection ORDER BY severity_points DESC;
```
Compare `error-flag` against `reread`, `measure` and `probe`. If the
cheap methods catch the expensive failures, make them routine.

## Repeat offenders (the same class twice)
```sql
SELECT class, COUNT(*) AS times, GROUP_CONCAT(failure_id) AS ids
FROM failures GROUP BY class HAVING COUNT(*) > 1 ORDER BY times DESC;
```
`self-matching-kill` appearing twice in one session is the kind of thing this
query exists for.

## How late are failures caught?
```sql
SELECT exchanges_to_detect, COUNT(*) FROM failures GROUP BY exchanges_to_detect ORDER BY 1;
```

## Where does tool time go? (only calls with recorded durations)
```sql
SELECT family, ROUND(SUM(duration_s) / 60, 1) AS minutes, COUNT(*) AS timed_calls
FROM tool_calls WHERE duration_s IS NOT NULL GROUP BY family ORDER BY minutes DESC;
```

Treat every answer as a statement about the record, not the session. A tool
that never fails in `v_tool_reliability` may simply never have had its result
recorded. Check `unrecorded` before concluding anything.

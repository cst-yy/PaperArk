ANALYZE papers;
ANALYZE chunks;
ANALYZE sections;
ANALYZE "references";

-- The requested fixture is intentionally small enough that PostgreSQL can
-- prefer a sub-millisecond sequential scan. Disabling it below verifies that
-- each production predicate is indexable; normal planner choices are recorded
-- separately during validation.
SET enable_seqscan = off;

EXPLAIN (ANALYZE, BUFFERS)
SELECT id FROM papers WHERE title % 'QuantumChromodynamcs Needl';

EXPLAIN (ANALYZE, BUFFERS)
SELECT id FROM chunks
WHERE search_vector @@ websearch_to_tsquery('simple', 'unique-scale-term');

EXPLAIN (ANALYZE, BUFFERS)
SELECT id FROM sections
WHERE search_vector @@ websearch_to_tsquery('simple', 'unique-scale-term');

EXPLAIN (ANALYZE, BUFFERS)
SELECT id FROM "references"
WHERE search_vector @@ websearch_to_tsquery('simple', 'unique-scale-term');
EXPLAIN (ANALYZE, BUFFERS)
SELECT id
FROM notes
WHERE user_id = :'user_id'
  AND search_vector @@ websearch_to_tsquery('simple', 'unique-scale-term');

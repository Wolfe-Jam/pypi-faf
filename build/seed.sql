-- Seeds build/baseline.json: all-time downloads per package per day, counted
-- the way pypistats counts "overall / without_mirrors" (same Python-version
-- filter, same mirror list). Run on BigQuery:
--   bq query --use_legacy_sql=false --format=csv --max_rows=5000 < build/seed.sql
-- Sum each package's rows up to the seed date; that is its baseline total.
-- First run 2026-11-15, baselines through 2026-11-14 (about 100 GB scanned).
SELECT
  file.project AS package,
  DATE(timestamp) AS day,
  COUNT(*) AS downloads
FROM `bigquery-public-data.pypi.file_downloads`
WHERE DATE(timestamp) BETWEEN '2025-11-01' AND '2026-11-14'
  AND file.project IN ('claude-fafm-sdk','faf-agent-mcp','faf-python-sdk','gemini-faf-mcp','grok-faf-voice','slash-tokens')
  AND (REGEXP_CONTAINS(details.python, r'^[0-9]\.[0-9]+.{0,}$') OR details.python IS NULL)
  AND details.installer.name NOT IN ('bandersnatch','z3c.pypimirror','Artifactory','devpi')
GROUP BY package, day
ORDER BY package, day

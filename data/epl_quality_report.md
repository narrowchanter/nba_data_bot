# EPL Quality Report

**Last Updated:** TEMPLATE UTC
**Mode:** Pipeline scaffold

## Source Status

| Source | Freshness SLA | Status | Notes |
|--------|---------------|--------|-------|
| Fixtures | <= 6h | TEMPLATE | No live fixture ingestion yet |
| Table Snapshot | <= 24h | TEMPLATE | No live standings snapshot yet |
| Team Form | <= 24h | TEMPLATE | No rolling form dataset yet |
| Availability | <= 3h for same-day matches | TEMPLATE | No live availability ingestion yet |

## Run Summary

| Metric | Value |
|--------|-------|
| total_matches_ingested | 0 |
| fully_scorable_matches | 0 |
| skipped_matches | 0 |
| schema_drift_alerts | 0 |

## Guardrails

| Check | Result | Detail |
|-------|--------|--------|
| missing_fixture_ids | TEMPLATE | No live fixtures evaluated yet |
| ambiguous_team_mapping | TEMPLATE | No live club mapping evaluated yet |
| stale_table_snapshot | TEMPLATE | No live standings snapshot available yet |
| conflicting_availability | TEMPLATE | No live availability sources evaluated yet |

## Skip Reasons

| Reason | Count |
|--------|-------|
| missing_fixture_id | 0 |
| missing_team_mapping | 0 |
| stale_standings | 0 |
| conflicting_availability | 0 |

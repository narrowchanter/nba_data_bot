# Tennis Quality Report

**Last Updated:** TEMPLATE UTC
**Mode:** Template scaffold
**Spec:** `docs/TENNIS_Data_Bot_Spec.md`

## Source Status

| Source | Freshness SLA | Status | Notes |
|--------|---------------|--------|-------|
| Schedule | <= 6h | TEMPLATE | No live schedule ingestion yet |
| Rankings | <= 72h | TEMPLATE | No rankings snapshot yet |
| Stats | <= 7d | TEMPLATE | No historical stats ingestion yet |
| Availability | <= 2h for near-start matches | TEMPLATE | No injury or withdrawal ingestion yet |

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
| missing_surface | TEMPLATE | No live matches evaluated yet |
| player_identity_mapping | TEMPLATE | No live matches evaluated yet |
| stale_rankings_snapshot | TEMPLATE | No live snapshot available yet |
| conflicting_status_sources | TEMPLATE | No live availability sources evaluated yet |

## Skip Reasons

| Reason | Count |
|--------|-------|
| missing_surface | 0 |
| missing_player_mapping | 0 |
| stale_rankings | 0 |
| conflicting_status | 0 |

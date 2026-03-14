# EPL Quality Report

**Last Updated:** 2026-03-14 00:00 UTC
**Mode:** Pipeline scaffold with player stats, injuries, and sanity coverage

## Source Status

| source | freshness_sla | status | records | notes |
|--------|---------------|--------|---------|-------|
| Fixtures | <= 6h | SCAFFOLD | 1 | Fixture row is stable and fresh enough for the sample join. |
| Table Snapshot | <= 24h | SCAFFOLD | 2 | Strength rows drive points and goal-difference deltas. |
| Team Form | <= 24h | SCAFFOLD | 2 | Form rows back the rolling performance features. |
| Player Stats | <= 24h | SCAFFOLD | 4 | Player rows render in a dedicated section and quality coverage table. |
| Injuries | <= 6h on match day | SCAFFOLD | 3 | Injury watch remains separate from the matchup feature table. |

## Run Summary

| metric | value |
|--------|-------|
| total_matches_ingested | 1 |
| fully_scorable_matches | 1 |
| skipped_matches | 0 |
| player_stats_rows | 4 |
| injury_rows | 3 |
| schema_drift_alerts | 0 |

## Coverage

| metric | value |
|--------|-------|
| matches_with_player_stats | 1 |
| matches_with_injury_data | 1 |
| player_stats_coverage_pct | 100 |
| injury_coverage_pct | 100 |
| oldest_source_age_hours | 3.5 |
| latest_source_updated_at | 2026-03-13 20:30 UTC |

## Guardrails

| check | result | detail |
|-------|--------|--------|
| missing_fixture_ids | PASS | Sample fixture row has a stable match identifier. |
| ambiguous_team_mapping | PASS | Home and away clubs resolve cleanly through the scaffold join. |
| stale_table_snapshot | PASS | Oldest source age is 3.5h. |
| player_stats_coverage | PASS | Player-stat snapshot covers both clubs in the sample match. |
| conflicting_injuries | PASS | No duplicated player injuries disagree on status. |
| candidate_row_sanity | PASS | Feature frame passed row-count, null, and freshness validation. |

## Sanity Checks

| check | result | detail |
|-------|--------|--------|
| candidate_row_schema | PASS | 1 row validated against required EPL feature columns. |
| score_bounds | PASS | Sample result uses integer scores within the configured 0-20 bounds. |
| source_freshness | PASS | Freshness gate accepted the sample sources under the 2D limit. |
| player_stats_shape | PASS | Player-stat rows include goals, assists, shots on target, and chance creation. |
| injury_shape | PASS | Injury rows include status, return horizon, source, and confidence. |

## Skip Reasons

| reason | count |
|--------|-------|
| missing_fixture_id | 0 |
| missing_team_mapping | 0 |
| missing_player_stats | 0 |
| missing_injury_mapping | 0 |
| stale_standings | 0 |
| conflicting_injuries | 0 |

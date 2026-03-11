# Tennis Matches Today

**Last Updated:** TEMPLATE UTC
**Mode:** Template scaffold
**Spec:** `docs/TENNIS_Data_Bot_Spec.md`

## Schedule Sources

| Source | Website | Status | Records | Notes |
|--------|---------|--------|---------|-------|
| Match Schedule | Official ATP/WTA pages | TEMPLATE | 0 | Placeholder until schedule ingestion lands |
| Fallback Schedule | Mirror provider | OPTIONAL | 0 | Placeholder until fallback schedule adapter lands |

## Matches

| match_id | event_name | tour | surface | round | scheduled_utc | player_a | player_b | best_of | quality_state |
|----------|------------|------|---------|-------|---------------|----------|----------|---------|---------------|
| example_masters_r32_player_a_player_b_2026-03-11 | Example Masters | ATP | hard | R32 | 2026-03-11 12:00 UTC | Player A | Player B | 3 | TEMPLATE |

## Pre-Start Watchlist

| match_id | scheduled_utc | refresh_window | note |
|----------|---------------|----------------|------|
| example_masters_r32_player_a_player_b_2026-03-11 | 2026-03-11 12:00 UTC | T-120 to T-15 | Replace with near-start refresh candidates |

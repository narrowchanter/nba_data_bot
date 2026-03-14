# EPL Matches Today

**Last Updated:** 2026-03-14 00:00 UTC
**Mode:** Pipeline scaffold with player stats and injury monitoring

## Schedule Sources

| source | website | status | records | notes |
|--------|---------|--------|---------|-------|
| Fixtures | premierleague.com | SCAFFOLD | 1 | Sample scheduled row mirrors the candidate match shell. |
| Player Stats | club and event feeds | SCAFFOLD | 4 | Player-stat context can be refreshed alongside the schedule view. |
| Injuries | club reports and news feeds | SCAFFOLD | 3 | Injury rows are surfaced for pre-kickoff monitoring. |
| Market Snapshot | execution venue | OPTIONAL | 0 | Odds integration remains outside the scaffolded pipeline. |

## Matches

| match_id | kickoff_utc | home_team | away_team | venue | status | quality_state |
|----------|-------------|-----------|-----------|-------|--------|---------------|
| sample_epl_arsenal_chelsea_2026-03-14 | 2026-03-14 15:00 UTC | Arsenal | Chelsea | Emirates Stadium | scheduled | sanity_checked |

## Injury Watch

| match_id | team | player | status | refresh_window |
|----------|------|--------|--------|----------------|
| sample_epl_arsenal_chelsea_2026-03-14 | Arsenal | Gabriel Jesus | out | T-180 to T-30 |
| sample_epl_arsenal_chelsea_2026-03-14 | Chelsea | Reece James | questionable | T-180 to T-30 |
| sample_epl_arsenal_chelsea_2026-03-14 | Chelsea | Romeo Lavia | out | T-180 to T-30 |

## Pre-Kickoff Watchlist

| match_id | kickoff_utc | refresh_window | player_stats_refresh | injury_refresh | note |
|----------|-------------|----------------|----------------------|----------------|------|
| sample_epl_arsenal_chelsea_2026-03-14 | 2026-03-14 15:00 UTC | T-120 to T-15 | lineup-confirmed creators and finishers | club report plus manager availability update | Re-run matchup quality checks after final injury confirmation. |

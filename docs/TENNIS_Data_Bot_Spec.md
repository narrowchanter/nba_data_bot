# Tennis Data Bot Specification

## 1) Objective

Build a production-grade tennis data pipeline that mirrors the NBA bot philosophy:
- deterministic scheduled ingestion,
- normalized markdown/flat-file outputs for downstream agents,
- stable feature set for edge scoring,
- explicit data-quality guards before any execution decisions.

Primary consumer: a betting/execution agent (e.g., Gina MCP workflow) that needs structured, fresh, explainable tennis matchup data.

---

## 2) Scope

Initial scope (v1):
- ATP + WTA main-tour matches (plus optional Challenger/ITF toggle)
- Singles only
- Pre-match markets (winner, spread/games/sets if available)
- Daily refresh cadence + near-start refresh window

Out of scope (v1):
- In-play betting
- Doubles
- Full point-by-point live modeling

---

## 3) Data Sources

Use at least 2 independent sources per domain when possible.

### Core match schedule/results
- Official ATP/WTA event pages/APIs (if accessible)
- Flashscore/SofaScore-like schedule mirror (fallback)

### Rankings and player context
- ATP/WTA rankings (official + cached snapshots)
- Elo-like ratings (global + surface-specific)

### Performance stats (historical)
- Last-52-week record by surface
- Hold % / Break %
- Service points won / return points won
- Tiebreak record
- Straight-set win rate

### Availability/injury/withdrawals
- Official tournament withdrawal lists
- Player status/news feed parsing (tagged confidence)

### Market data (optional in this bot, required for execution layer)
- Prediction/odds venue API for line snapshots
- Timestamped line history for drift analysis

---

## 4) Repository Layout (target)

```text
.
├─ main_tennis.py
├─ scraper/
│  ├─ tennis_schedule.py
│  ├─ tennis_rankings.py
│  ├─ tennis_stats.py
│  ├─ tennis_injuries.py
│  ├─ tennis_markets.py         # optional adapter if needed
│  └─ tennis_features.py
├─ data/
│  ├─ tennis_data.md
│  ├─ tennis_players.md
│  ├─ tennis_matches_today.md
│  └─ tennis_quality_report.md
├─ outputs/
│  └─ tennis_run_YYYY-MM-DD_HHMMSS.txt
└─ docs/
   └─ TENNIS_Data_Bot_Spec.md
```

---

## 5) Canonical Data Schema

## Match entity
- `match_id` (stable key: tournament + round + player_a + player_b + date)
- `event_name`
- `tour` (`ATP` | `WTA` | `CH` | `ITF`)
- `surface` (`hard` | `clay` | `grass` | `indoor_hard`)
- `round`
- `scheduled_utc`
- `player_a`, `player_b`
- `best_of` (3/5)

## Player snapshot (per run)
- `player_id`
- `name`
- `ranking`
- `elo_global`
- `elo_surface`
- `age`
- `handedness`
- `country`

## Form/stat features (per player per surface window)
- `last10_wins`
- `surface_last20_wins`
- `hold_pct`
- `break_pct`
- `spw_pct` (service points won)
- `rpw_pct` (return points won)
- `tb_win_pct`
- `retirement_rate_52w`

## Matchup feature row
- `match_id`
- `surface`
- `rank_delta`
- `elo_delta_global`
- `elo_delta_surface`
- `hold_break_composite_delta`
- `form_delta`
- `fatigue_delta` (rest days + prior match duration proxy)
- `injury_flag_a`, `injury_flag_b`
- `withdrawal_risk_score_a`, `withdrawal_risk_score_b`
- `model_win_prob_a`, `model_win_prob_b`
- `confidence_grade`

---

## 6) Ingestion & Update Cadence

## Standard cadence
- Full refresh every 6 hours (UTC)
- Incremental refresh every 30 minutes on match days

## Pre-start critical window
For matches starting within next 2 hours:
- refresh every 10–15 minutes,
- re-evaluate injury/withdrawal and lineup status,
- write a delta report.

## Retention
- Keep rolling 30-day snapshots for match/feature rows
- Keep run logs indefinitely (compressed monthly)

---

## 7) Feature Engineering (Tennis-specific)

Composite signal should blend:
1. **Long-run strength**
   - global elo + ranking tier
2. **Surface suitability**
   - surface elo + surface record
3. **Serve/return matchup**
   - hold% vs opponent break% interaction
4. **Current form**
   - last 10 + last 30 day trend
5. **Durability/risk**
   - retirements, medical timeouts, withdrawals, compressed schedule

Example model blend:
- `win_score = 0.30*elo_surface_delta + 0.20*elo_global_delta + 0.20*serve_return_delta + 0.15*form_delta + 0.15*durability_delta`
- transform score -> probability with calibrated logistic function.

Output both:
- raw score,
- calibrated probability,
- confidence bucket (`A/B/C`) tied to data completeness and model agreement.

---

## 8) Data Quality & Guardrails

Hard fail conditions:
- missing surface for match
- missing one player identity mapping
- stale rankings snapshot (>72h)
- conflicting player status from primary sources without tie-break rule

Soft fail / downgrade confidence:
- injury status sourced from low-confidence text only
- limited sample size on surface (<8 recent matches)

Quality report each run (`data/tennis_quality_report.md`):
- total matches ingested
- fully scorable matches
- skipped matches + reason counts
- stale source checks
- schema drift alerts

---

## 9) Injury / Withdrawal Handling

Create normalized status model:
- `available`
- `questionable`
- `likely_out`
- `withdrawn`

Each status carries:
- `source`
- `source_ts`
- `confidence` (0–1)

Rules:
- `withdrawn` => match removed from candidate set
- `likely_out` => confidence cap at C unless confirmed elsewhere
- significant status change within 2h of match => force immediate re-score

---

## 10) Market Mapping Layer (for execution compatibility)

Even if execution is external, this bot should emit mapping-ready records:
- `external_event_slug`
- `external_market_id`
- `side_a_token`, `side_b_token`
- `last_seen_price_a`, `last_seen_price_b`
- `market_snapshot_ts`

Matching logic:
1. exact player-name normalization
2. event date window +/- 1 day
3. round sanity check when available
4. confidence score for mapping (`exact`, `probable`, `manual_review`)

---

## 11) Cron Workflow (recommended)

1. **Morning baseline run** (full refresh)
2. **Hourly scan** (candidate generation)
3. **T-120 dry run** (decision preview)
4. **T-30 dry run** (stability check)
5. **Execution handoff window** (external agent decides live orders)
6. **Post-event reconcile run** (results + model calibration updates)

---

## 12) Integration with Gina-like Execution Layer

Data bot responsibilities:
- publish candidate rows + probabilities + confidence + quality flags
- never place trades directly

Execution layer responsibilities (e.g., Gina MCP):
- read candidate payload
- compare model probability vs market implied probability
- apply risk caps and liquidity checks
- place/cancel/redeem orders

Contract between systems:
- stable schema file (markdown + optional JSON export)
- explicit field names for `model_prob`, `edge`, `confidence`, `quality_state`

---

## 13) Edge Interpretation Framework

Definitions:
- `implied_prob` from market
- `model_prob` from tennis model
- `edge = model_prob - implied_prob`

Execution guidance tiers:
- `edge < 0.03`: no trade
- `0.03 <= edge < 0.06`: small size only if confidence A/B
- `0.06 <= edge < 0.10`: standard size
- `>= 0.10`: high conviction, still capped by bankroll + liquidity

Confidence overrides edge:
- Confidence C cannot exceed reduced sizing regardless of edge magnitude.

---

## 14) Implementation Roadmap

## Phase 1 (MVP)
- Build schedule + ranking + basic stats scrapers
- Emit `tennis_data.md` and `tennis_matches_today.md`
- Create deterministic `match_id` and normalized player dictionary

## Phase 2 (Modelable features)
- Add surface-aware features + form windows
- Add composite win score + calibrated probability
- Add quality report and skip reasons

## Phase 3 (Execution-ready)
- Add market mapping output fields
- Add implied probability + edge computation hooks
- Add run artifacts and delta summaries

## Phase 4 (Reliability)
- Add schema tests + source freshness checks
- Add backfill scripts and replay mode
- Add calibration notebook/report for probability quality

---

## 15) Acceptance Criteria

- Daily runs complete without manual intervention
- >90% of listed ATP/WTA singles matches produce scorable feature rows
- Each run emits:
  - candidate list,
  - quality report,
  - stable markdown outputs
- Data freshness SLA met for pre-start windows
- Clear handoff contract works with Gina-like execution layer

---

## 16) Open Questions

- Source licensing constraints for chosen stats feeds
- Whether to include bookmaker odds alongside prediction market prices
- Surface transitions early season (small sample instability)
- Best calibration approach per tour/surface (global vs segmented)

import unittest

import pandas as pd

from epl.features import EPLSanityCheckError, build_matchup_features, sanity_check_candidate_rows

EXPECTED_CANDIDATE_COLUMNS = [
    "match_id",
    "season",
    "kickoff_ts",
    "home_team",
    "away_team",
    "home_score",
    "away_score",
    "strength_points_per_match_delta",
    "strength_goal_diff_per_match_delta",
    "strength_goals_for_per_match_delta",
    "strength_goals_against_per_match_delta",
    "form_points_per_match_delta",
    "form_goal_diff_per_match_delta",
    "home_advantage_points_per_match_delta",
    "home_advantage_goal_diff_per_match_delta",
    "player_influence_proxy_delta",
    "availability_adjusted_player_influence_proxy_delta",
    "player_availability_headwind_proxy_delta",
    "result_goal_diff",
    "result_total_goals",
    "result_home_win",
    "result_draw",
    "result_away_win",
    "fixtures_updated_at",
    "home_strength_updated_at",
    "away_strength_updated_at",
    "home_form_updated_at",
    "away_form_updated_at",
    "home_player_stats_updated_at",
    "away_player_stats_updated_at",
    "home_player_availability_updated_at",
    "away_player_availability_updated_at",
    "oldest_source_updated_at",
    "latest_source_updated_at",
    "feature_generated_at",
]


def make_ingest_tables() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    fixtures = pd.DataFrame(
        [
            {
                "match_id": "2025-ars-che",
                "season": "2025-26",
                "kickoff_ts": "2025-08-17T16:30:00Z",
                "home_team": "Arsenal",
                "away_team": "Chelsea",
                "home_score": 2,
                "away_score": 1,
                "updated_at": "2025-08-18T00:00:00Z",
            },
            {
                "match_id": "2025-liv-new",
                "season": "2025-26",
                "kickoff_ts": "2025-08-18T19:00:00Z",
                "home_team": "Liverpool",
                "away_team": "Newcastle",
                "home_score": 3,
                "away_score": 0,
                "updated_at": "2025-08-18T00:15:00Z",
            },
        ]
    )
    team_strength = pd.DataFrame(
        [
            {
                "season": "2025-26",
                "team": "Arsenal",
                "matches_played": 20,
                "points": 44,
                "goal_diff": 24,
                "goals_for": 38,
                "goals_against": 14,
                "home_matches": 10,
                "home_points": 24,
                "home_goal_diff": 14,
                "away_matches": 10,
                "away_points": 20,
                "away_goal_diff": 10,
                "updated_at": "2025-08-18T01:00:00Z",
            },
            {
                "season": "2025-26",
                "team": "Chelsea",
                "matches_played": 20,
                "points": 34,
                "goal_diff": 8,
                "goals_for": 30,
                "goals_against": 22,
                "home_matches": 10,
                "home_points": 18,
                "home_goal_diff": 5,
                "away_matches": 10,
                "away_points": 16,
                "away_goal_diff": 3,
                "updated_at": "2025-08-18T01:15:00Z",
            },
            {
                "season": "2025-26",
                "team": "Liverpool",
                "matches_played": 20,
                "points": 48,
                "goal_diff": 28,
                "goals_for": 42,
                "goals_against": 14,
                "home_matches": 10,
                "home_points": 28,
                "home_goal_diff": 18,
                "away_matches": 10,
                "away_points": 20,
                "away_goal_diff": 10,
                "updated_at": "2025-08-18T01:30:00Z",
            },
            {
                "season": "2025-26",
                "team": "Newcastle",
                "matches_played": 20,
                "points": 32,
                "goal_diff": 4,
                "goals_for": 31,
                "goals_against": 27,
                "home_matches": 10,
                "home_points": 20,
                "home_goal_diff": 6,
                "away_matches": 10,
                "away_points": 12,
                "away_goal_diff": -2,
                "updated_at": "2025-08-18T01:45:00Z",
            },
        ]
    )
    team_form = pd.DataFrame(
        [
            {
                "season": "2025-26",
                "team": "Arsenal",
                "window_matches": 5,
                "window_points": 11,
                "window_goal_diff": 7,
                "updated_at": "2025-08-18T02:00:00Z",
            },
            {
                "season": "2025-26",
                "team": "Chelsea",
                "window_matches": 5,
                "window_points": 7,
                "window_goal_diff": 1,
                "updated_at": "2025-08-18T02:05:00Z",
            },
            {
                "season": "2025-26",
                "team": "Liverpool",
                "window_matches": 5,
                "window_points": 13,
                "window_goal_diff": 9,
                "updated_at": "2025-08-18T02:10:00Z",
            },
            {
                "season": "2025-26",
                "team": "Newcastle",
                "window_matches": 5,
                "window_points": 6,
                "window_goal_diff": -1,
                "updated_at": "2025-08-18T02:15:00Z",
            },
        ]
    )
    return fixtures, team_strength, team_form


def make_player_tables() -> tuple[pd.DataFrame, pd.DataFrame]:
    player_stats = pd.DataFrame(
        [
            {
                "season": "2025-26",
                "team": "Arsenal",
                "player": "Bukayo Saka",
                "minutes_played": 1800,
                "goals": 10,
                "assists": 8,
                "shots_on_target": 25,
                "chances_created": 50,
                "updated_at": "2025-08-18T02:20:00Z",
            },
            {
                "season": "2025-26",
                "team": "Arsenal",
                "player": "Martin Odegaard",
                "minutes_played": 1700,
                "goals": 5,
                "assists": 7,
                "shots_on_target": 18,
                "chances_created": 45,
                "updated_at": "2025-08-18T02:25:00Z",
            },
            {
                "season": "2025-26",
                "team": "Chelsea",
                "player": "Cole Palmer",
                "minutes_played": 1750,
                "goals": 8,
                "assists": 6,
                "shots_on_target": 20,
                "chances_created": 40,
                "updated_at": "2025-08-18T02:30:00Z",
            },
            {
                "season": "2025-26",
                "team": "Chelsea",
                "player": "Nicolas Jackson",
                "minutes_played": 1600,
                "goals": 7,
                "assists": 3,
                "shots_on_target": 22,
                "chances_created": 18,
                "updated_at": "2025-08-18T02:35:00Z",
            },
            {
                "season": "2025-26",
                "team": "Liverpool",
                "player": "Mohamed Salah",
                "minutes_played": 1800,
                "goals": 12,
                "assists": 8,
                "shots_on_target": 28,
                "chances_created": 44,
                "updated_at": "2025-08-18T02:40:00Z",
            },
        ]
    )
    player_availability = pd.DataFrame(
        [
            {
                "season": "2025-26",
                "team": "Arsenal",
                "player": "Bukayo Saka",
                "status": "Questionable",
                "updated_at": "2025-08-18T03:00:00Z",
            },
            {
                "season": "2025-26",
                "team": "Arsenal",
                "player": "Martin Odegaard",
                "status": "Available",
                "updated_at": "2025-08-18T03:05:00Z",
            },
            {
                "season": "2025-26",
                "team": "Chelsea",
                "player": "Cole Palmer",
                "status": "Available",
                "updated_at": "2025-08-18T03:10:00Z",
            },
            {
                "season": "2025-26",
                "team": "Chelsea",
                "player": "Nicolas Jackson",
                "status": "Doubtful",
                "updated_at": "2025-08-18T03:12:00Z",
            },
            {
                "season": "2025-26",
                "team": "Newcastle",
                "player": "Alexander Isak",
                "status": "Out",
                "updated_at": "2025-08-18T03:15:00Z",
            },
        ]
    )
    return player_stats, player_availability


class BuildMatchupFeaturesTests(unittest.TestCase):
    def test_build_matchup_features_emits_expected_deltas_and_column_order(self) -> None:
        fixtures, team_strength, team_form = make_ingest_tables()
        player_stats, player_availability = make_player_tables()

        candidate_rows = build_matchup_features(
            fixtures,
            team_strength,
            team_form,
            player_stats,
            player_availability,
            feature_generated_at="2025-08-18T03:30:00Z",
        )

        self.assertEqual(len(candidate_rows), 2)
        self.assertEqual(EXPECTED_CANDIDATE_COLUMNS, list(candidate_rows.columns))

        arsenal_row = candidate_rows.loc[candidate_rows["match_id"] == "2025-ars-che"].iloc[0]
        self.assertAlmostEqual(arsenal_row["strength_points_per_match_delta"], 0.5)
        self.assertAlmostEqual(arsenal_row["strength_goal_diff_per_match_delta"], 0.8)
        self.assertAlmostEqual(arsenal_row["form_points_per_match_delta"], 0.8)
        self.assertAlmostEqual(arsenal_row["home_advantage_points_per_match_delta"], 0.8)
        self.assertAlmostEqual(arsenal_row["player_influence_proxy_delta"], 13.016667, places=6)
        self.assertAlmostEqual(
            arsenal_row["availability_adjusted_player_influence_proxy_delta"],
            10.675000,
            places=6,
        )
        self.assertAlmostEqual(
            arsenal_row["player_availability_headwind_proxy_delta"],
            2.341667,
            places=6,
        )
        self.assertEqual(int(arsenal_row["result_home_win"]), 1)
        self.assertEqual(pd.Timestamp("2025-08-18T00:00:00Z"), arsenal_row["oldest_source_updated_at"])

    def test_build_matchup_features_preserves_fixture_coverage_with_partial_player_joins(self) -> None:
        fixtures, team_strength, team_form = make_ingest_tables()
        player_stats, player_availability = make_player_tables()

        candidate_rows = build_matchup_features(
            fixtures,
            team_strength,
            team_form,
            player_stats,
            player_availability,
            feature_generated_at="2025-08-18T03:30:00Z",
        )

        self.assertEqual(["2025-ars-che", "2025-liv-new"], candidate_rows["match_id"].tolist())
        self.assertFalse(
            candidate_rows[
                [
                    "player_influence_proxy_delta",
                    "availability_adjusted_player_influence_proxy_delta",
                    "player_availability_headwind_proxy_delta",
                ]
            ]
            .isna()
            .any()
            .any()
        )

        liverpool_row = candidate_rows.loc[candidate_rows["match_id"] == "2025-liv-new"].iloc[0]
        self.assertAlmostEqual(liverpool_row["player_influence_proxy_delta"], 46.6, places=6)
        self.assertAlmostEqual(
            liverpool_row["availability_adjusted_player_influence_proxy_delta"],
            46.6,
            places=6,
        )
        self.assertAlmostEqual(liverpool_row["player_availability_headwind_proxy_delta"], 0.0, places=6)
        self.assertEqual(
            pd.Timestamp("2025-08-18T03:15:00Z"),
            liverpool_row["away_player_availability_updated_at"],
        )
        self.assertEqual(
            pd.Timestamp("2025-08-18T03:15:00Z"),
            liverpool_row["latest_source_updated_at"],
        )

    def test_build_matchup_features_defaults_missing_optional_player_sources_to_zero_deltas(self) -> None:
        fixtures, team_strength, team_form = make_ingest_tables()

        candidate_rows = build_matchup_features(
            fixtures,
            team_strength,
            team_form,
            feature_generated_at="2025-08-18T03:30:00Z",
        )

        self.assertTrue((candidate_rows["player_influence_proxy_delta"] == 0.0).all())
        self.assertTrue((candidate_rows["availability_adjusted_player_influence_proxy_delta"] == 0.0).all())
        self.assertTrue((candidate_rows["player_availability_headwind_proxy_delta"] == 0.0).all())
        self.assertTrue(candidate_rows["home_player_stats_updated_at"].isna().all())
        self.assertTrue(candidate_rows["away_player_availability_updated_at"].isna().all())

    def test_build_matchup_features_player_deltas_stay_in_sample_sanity_range(self) -> None:
        fixtures, team_strength, team_form = make_ingest_tables()
        player_stats, player_availability = make_player_tables()

        candidate_rows = build_matchup_features(
            fixtures,
            team_strength,
            team_form,
            player_stats,
            player_availability,
            feature_generated_at="2025-08-18T03:30:00Z",
        )

        for column_name in (
            "player_influence_proxy_delta",
            "availability_adjusted_player_influence_proxy_delta",
            "player_availability_headwind_proxy_delta",
        ):
            with self.subTest(column_name=column_name):
                self.assertTrue(candidate_rows[column_name].abs().lt(75).all())


class SanityCheckCandidateRowsTests(unittest.TestCase):
    def setUp(self) -> None:
        fixtures, team_strength, team_form = make_ingest_tables()
        player_stats, player_availability = make_player_tables()
        self.candidate_rows = build_matchup_features(
            fixtures,
            team_strength,
            team_form,
            player_stats,
            player_availability,
            feature_generated_at="2025-08-18T03:30:00Z",
        )

    def test_sanity_check_candidate_rows_accepts_clean_rows(self) -> None:
        summary = sanity_check_candidate_rows(
            self.candidate_rows,
            expected_rows=2,
            current_time="2025-08-19T00:00:00Z",
            max_staleness="2D",
        )

        self.assertEqual(summary["row_count"], 2)
        self.assertEqual(summary["key_columns"], ["season", "match_id"])
        self.assertGreaterEqual(summary["oldest_source_age_hours"], 0)

    def test_sanity_check_candidate_rows_rejects_row_count_mismatch(self) -> None:
        with self.assertRaisesRegex(EPLSanityCheckError, "row count mismatch"):
            sanity_check_candidate_rows(
                self.candidate_rows,
                expected_rows=3,
                current_time="2025-08-19T00:00:00Z",
                max_staleness="2D",
            )

    def test_sanity_check_candidate_rows_rejects_nulls(self) -> None:
        broken_rows = self.candidate_rows.copy()
        broken_rows.loc[0, "availability_adjusted_player_influence_proxy_delta"] = pd.NA

        with self.assertRaisesRegex(EPLSanityCheckError, "required column nulls"):
            sanity_check_candidate_rows(
                broken_rows,
                expected_rows=2,
                current_time="2025-08-19T00:00:00Z",
                max_staleness="2D",
            )

    def test_sanity_check_candidate_rows_rejects_duplicate_keys(self) -> None:
        broken_rows = pd.concat([self.candidate_rows, self.candidate_rows.iloc[[0]]], ignore_index=True)

        with self.assertRaisesRegex(EPLSanityCheckError, "duplicate candidate keys"):
            sanity_check_candidate_rows(
                broken_rows,
                current_time="2025-08-19T00:00:00Z",
                max_staleness="2D",
            )

    def test_sanity_check_candidate_rows_rejects_bad_scores(self) -> None:
        broken_rows = self.candidate_rows.copy()
        broken_rows.loc[0, "home_score"] = 99

        with self.assertRaisesRegex(EPLSanityCheckError, "outside score bounds"):
            sanity_check_candidate_rows(
                broken_rows,
                current_time="2025-08-19T00:00:00Z",
                max_staleness="2D",
            )

    def test_sanity_check_candidate_rows_rejects_stale_timestamps(self) -> None:
        broken_rows = self.candidate_rows.copy()
        broken_rows.loc[:, "oldest_source_updated_at"] = pd.Timestamp("2025-07-01T00:00:00Z")

        with self.assertRaisesRegex(EPLSanityCheckError, "stale source timestamps"):
            sanity_check_candidate_rows(
                broken_rows,
                current_time="2025-08-19T00:00:00Z",
                max_staleness="2D",
            )


if __name__ == "__main__":
    unittest.main()

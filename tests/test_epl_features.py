import unittest

import pandas as pd

from epl.features import EPLSanityCheckError, build_matchup_features, sanity_check_candidate_rows


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


class BuildMatchupFeaturesTests(unittest.TestCase):
    def test_build_matchup_features_emits_expected_deltas(self) -> None:
        fixtures, team_strength, team_form = make_ingest_tables()

        candidate_rows = build_matchup_features(
            fixtures,
            team_strength,
            team_form,
            feature_generated_at="2025-08-18T03:00:00Z",
        )

        self.assertEqual(len(candidate_rows), 2)
        arsenal_row = candidate_rows.loc[candidate_rows["match_id"] == "2025-ars-che"].iloc[0]
        self.assertAlmostEqual(arsenal_row["strength_points_per_match_delta"], 0.5)
        self.assertAlmostEqual(arsenal_row["strength_goal_diff_per_match_delta"], 0.8)
        self.assertAlmostEqual(arsenal_row["form_points_per_match_delta"], 0.8)
        self.assertAlmostEqual(arsenal_row["home_advantage_points_per_match_delta"], 0.8)
        self.assertEqual(int(arsenal_row["result_home_win"]), 1)
        self.assertEqual(pd.Timestamp("2025-08-18T00:00:00Z"), arsenal_row["oldest_source_updated_at"])


class SanityCheckCandidateRowsTests(unittest.TestCase):
    def setUp(self) -> None:
        fixtures, team_strength, team_form = make_ingest_tables()
        self.candidate_rows = build_matchup_features(
            fixtures,
            team_strength,
            team_form,
            feature_generated_at="2025-08-18T03:00:00Z",
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
        broken_rows.loc[0, "form_points_per_match_delta"] = pd.NA

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

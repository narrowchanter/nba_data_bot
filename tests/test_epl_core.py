import unittest
from datetime import date, datetime, timezone

from scraper.epl import (
    MatchIdentity,
    build_match_identity,
    build_match_key,
    get_team_id,
    normalize_match_date,
    normalize_team_name,
)


class NormalizeTeamNameTests(unittest.TestCase):
    def test_normalize_team_name_handles_common_aliases(self):
        cases = {
            "  man utd  ": "Manchester United",
            "Spurs": "Tottenham Hotspur",
            "Brighton & Hove Albion": "Brighton and Hove Albion",
            "Nott'm Forest": "Nottingham Forest",
            "WOLVES": "Wolverhampton Wanderers",
        }

        for raw_name, expected_name in cases.items():
            with self.subTest(raw_name=raw_name):
                self.assertEqual(normalize_team_name(raw_name), expected_name)

    def test_normalize_team_name_rejects_unknown_teams(self):
        with self.assertRaisesRegex(ValueError, "Unknown EPL team name"):
            normalize_team_name("Barcelona")

    def test_normalize_team_name_rejects_blank_values(self):
        with self.assertRaisesRegex(ValueError, "Team name is required"):
            normalize_team_name("   ")

    def test_get_team_id_uses_canonical_ids(self):
        self.assertEqual(get_team_id("Man City"), "man-city")
        self.assertEqual(get_team_id("West Ham"), "west-ham")


class NormalizeMatchDateTests(unittest.TestCase):
    def test_normalize_match_date_accepts_supported_input_types(self):
        cases = (
            (date(2026, 3, 14), "2026-03-14"),
            (datetime(2026, 3, 14, 15, 30, tzinfo=timezone.utc), "2026-03-14"),
            ("2026-03-14", "2026-03-14"),
            ("2026-03-14T15:30:00Z", "2026-03-14"),
            ("2026/03/14", "2026-03-14"),
            ("14/03/2026", "2026-03-14"),
        )

        for raw_date, expected_date in cases:
            with self.subTest(raw_date=raw_date):
                self.assertEqual(normalize_match_date(raw_date), expected_date)

    def test_normalize_match_date_rejects_bad_values(self):
        with self.assertRaisesRegex(ValueError, "Unsupported match date format"):
            normalize_match_date("03-14-2026")

        with self.assertRaisesRegex(TypeError, "Match date must be a date, datetime, or string"):
            normalize_match_date(20260314)


class BuildMatchKeyTests(unittest.TestCase):
    def test_build_match_identity_returns_normalized_values(self):
        self.assertEqual(
            build_match_identity("  Spurs ", "wolves", "2026-03-14"),
            MatchIdentity(
                match_date="2026-03-14",
                home_team="Tottenham Hotspur",
                away_team="Wolverhampton Wanderers",
            ),
        )

    def test_build_match_key_uses_normalized_team_ids(self):
        self.assertEqual(
            build_match_key("Man Utd", "Brighton & Hove Albion", "2026-03-14T17:30:00Z"),
            "epl__2026-03-14__man-united__brighton",
        )

    def test_build_match_key_preserves_home_away_order(self):
        self.assertNotEqual(
            build_match_key("Arsenal", "Chelsea", "2026-03-14"),
            build_match_key("Chelsea", "Arsenal", "2026-03-14"),
        )

    def test_build_match_key_rejects_duplicate_teams_after_normalization(self):
        with self.assertRaisesRegex(ValueError, "Home and away teams must be different"):
            build_match_key("Manchester United", "man utd", "2026-03-14")


if __name__ == "__main__":
    unittest.main()

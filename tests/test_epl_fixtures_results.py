import unittest
from unittest.mock import patch

import pandas as pd
import requests

from scraper.epl_fixtures_results import (
    get_epl_fixtures,
    get_epl_fixtures_results,
    get_epl_results,
)


SAMPLE_PAYLOAD = [
    {
        "MatchNumber": 2,
        "RoundNumber": 1,
        "DateUtc": "2025-08-16 11:30:00Z",
        "Location": "Bravo Park",
        "HomeTeam": "Bravo",
        "AwayTeam": "Charlie",
        "HomeTeamScore": 1,
        "AwayTeamScore": 1,
    },
    {
        "MatchNumber": 1,
        "RoundNumber": 1,
        "DateUtc": "2025-08-15 19:00:00Z",
        "Location": "Alpha Park",
        "HomeTeam": "Alpha",
        "AwayTeam": "Bravo",
        "HomeTeamScore": 2,
        "AwayTeamScore": 0,
    },
    {
        "MatchNumber": 4,
        "RoundNumber": 2,
        "DateUtc": "2025-08-23 14:00:00Z",
        "Location": "Charlie Park",
        "HomeTeam": "Charlie",
        "AwayTeam": "Alpha",
        "HomeTeamScore": 0,
        "AwayTeamScore": 3,
    },
    {
        "MatchNumber": 3,
        "RoundNumber": 2,
        "DateUtc": "2025-08-22 19:00:00Z",
        "Location": "Delta Park",
        "HomeTeam": "Bravo",
        "AwayTeam": "Delta",
        "HomeTeamScore": None,
        "AwayTeamScore": None,
    },
]

EXPECTED_COLUMNS = [
    "MATCH_NUMBER",
    "ROUND_NUMBER",
    "KICKOFF_UTC",
    "LOCATION",
    "HOME_TEAM",
    "AWAY_TEAM",
    "STATUS",
    "HOME_SCORE",
    "AWAY_SCORE",
    "RESULT",
]


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


class EplFixturesResultsTests(unittest.TestCase):
    @patch("scraper.epl_common.requests.get", return_value=FakeResponse(SAMPLE_PAYLOAD))
    def test_get_epl_fixtures_results_normalizes_and_sorts_feed(self, mock_get):
        df = get_epl_fixtures_results(season_start_year=2025)

        self.assertEqual(list(df.columns), EXPECTED_COLUMNS)
        self.assertEqual(df["MATCH_NUMBER"].tolist(), [1, 2, 3, 4])
        self.assertEqual(df["KICKOFF_UTC"].tolist()[0], "2025-08-15T19:00:00Z")
        self.assertEqual(df["STATUS"].tolist(), ["completed", "completed", "scheduled", "completed"])
        self.assertEqual(df["RESULT"].tolist(), ["H", "D", "", "A"])

        scheduled = df[df["STATUS"] == "scheduled"].iloc[0]
        self.assertTrue(pd.isna(scheduled["HOME_SCORE"]))
        self.assertTrue(pd.isna(scheduled["AWAY_SCORE"]))
        mock_get.assert_called_once()

    @patch("scraper.epl_common.requests.get", return_value=FakeResponse(SAMPLE_PAYLOAD))
    def test_get_epl_results_filters_completed_matches(self, mock_get):
        df = get_epl_results(season_start_year=2025)

        self.assertEqual(df["MATCH_NUMBER"].tolist(), [1, 2, 4])
        self.assertTrue((df["STATUS"] == "completed").all())
        self.assertEqual(df["RESULT"].tolist(), ["H", "D", "A"])
        mock_get.assert_called_once()

    @patch("scraper.epl_common.requests.get", return_value=FakeResponse(SAMPLE_PAYLOAD))
    def test_get_epl_fixtures_filters_scheduled_matches(self, mock_get):
        df = get_epl_fixtures(season_start_year=2025)

        self.assertEqual(df["MATCH_NUMBER"].tolist(), [3])
        self.assertEqual(df.iloc[0]["HOME_TEAM"], "Bravo")
        self.assertEqual(df.iloc[0]["AWAY_TEAM"], "Delta")
        self.assertEqual(df.iloc[0]["STATUS"], "scheduled")
        mock_get.assert_called_once()

    @patch("scraper.epl_common.requests.get", side_effect=requests.Timeout("boom"))
    def test_network_errors_return_empty_schema(self, mock_get):
        df = get_epl_fixtures_results(season_start_year=2025)

        self.assertTrue(df.empty)
        self.assertEqual(list(df.columns), EXPECTED_COLUMNS)
        mock_get.assert_called_once()


if __name__ == "__main__":
    unittest.main()

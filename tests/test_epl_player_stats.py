import unittest
from unittest.mock import patch

import requests

from scraper.epl_player_stats import PLAYER_STATS_COLUMNS, get_epl_player_stats


SAMPLE_PAYLOAD = {
    "success": True,
    "players": [
        {
            "id": "101",
            "player_name": "Bukayo Saka",
            "team_title": "Arsenal",
            "position": "F M",
            "games": "25",
            "time": "2104",
            "goals": "12",
            "assists": "10",
            "yellow_cards": "4",
            "red_cards": "0",
        },
        {
            "id": "202",
            "player_name": "Mohamed Salah",
            "team_title": "Liverpool",
            "position": "F",
            "games": "26",
            "time": "2210",
            "goals": "18",
            "assists": "8",
            "yellow_cards": "1",
            "red_cards": "0",
        },
        {
            "id": "303",
            "player_name": "Joao Gomes",
            "team_title": "Wolverhampton Wanderers",
            "position": "M",
            "games": "24",
            "time": "1870",
            "goals": "3",
            "assists": "1",
            "yellow_cards": "9",
            "red_cards": "1",
        },
    ],
}


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


class EplPlayerStatsTests(unittest.TestCase):
    @patch("scraper.epl_player_stats.requests.post", return_value=FakeResponse(SAMPLE_PAYLOAD))
    def test_get_epl_player_stats_normalizes_and_sorts_player_rows(self, mock_post):
        df = get_epl_player_stats(season_start_year=2025)

        self.assertEqual(list(df.columns), PLAYER_STATS_COLUMNS)
        self.assertEqual(df["PLAYER_NAME"].tolist(), ["Mohamed Salah", "Bukayo Saka", "Joao Gomes"])
        self.assertEqual(df["GOALS"].tolist(), [18, 12, 3])
        self.assertEqual(df["ASSISTS"].tolist(), [8, 10, 1])
        self.assertEqual(df["YELLOW_CARDS"].tolist(), [1, 4, 9])
        self.assertEqual(df["RED_CARDS"].tolist(), [0, 0, 1])
        self.assertEqual(str(df["PLAYER_NAME"].dtype), "string")
        self.assertEqual(str(df["GOALS"].dtype), "Int64")

        mock_post.assert_called_once()
        self.assertEqual(mock_post.call_args.kwargs["data"], {"league": "EPL", "season": "2025"})

    @patch("scraper.epl_player_stats.requests.post", return_value=FakeResponse({"error": {"error_code": 4}}))
    def test_error_payload_returns_empty_schema(self, mock_post):
        df = get_epl_player_stats(season_start_year=2025)

        self.assertTrue(df.empty)
        self.assertEqual(list(df.columns), PLAYER_STATS_COLUMNS)
        mock_post.assert_called_once()

    @patch("scraper.epl_player_stats.requests.post", return_value=FakeResponse({"players": [{"games": "oops"}]}))
    def test_malformed_player_rows_return_empty_schema(self, mock_post):
        df = get_epl_player_stats(season_start_year=2025)

        self.assertTrue(df.empty)
        self.assertEqual(list(df.columns), PLAYER_STATS_COLUMNS)
        mock_post.assert_called_once()

    @patch("scraper.epl_player_stats.requests.post", side_effect=requests.Timeout("boom"))
    def test_network_errors_return_empty_schema(self, mock_post):
        df = get_epl_player_stats(season_start_year=2025)

        self.assertTrue(df.empty)
        self.assertEqual(list(df.columns), PLAYER_STATS_COLUMNS)
        self.assertEqual(str(df["GOALS"].dtype), "Int64")
        self.assertEqual(str(df["PLAYER_NAME"].dtype), "string")
        mock_post.assert_called_once()


if __name__ == "__main__":
    unittest.main()

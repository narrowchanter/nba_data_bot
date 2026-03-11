"""
ESPN-backed tennis season stats scraper.
"""

import pandas as pd

from .tennis_common import DEFAULT_TOURS, TOUR_LABELS, fetch_json, normalize_ref, normalize_tours, tour_slug
from .tennis_rankings import _get_athlete_payload, _get_ranking_payload


STAT_NAME_MAP = {
    "singlesWon": "SINGLES_WON",
    "singlesLost": "SINGLES_LOST",
    "singlesTitles": "SINGLES_TITLES",
    "doublesTitles": "DOUBLES_TITLES",
    "prize": "PRIZE_MONEY_USD",
}

STAT_COLUMNS = [
    "TOUR",
    "RANK",
    "PLAYER_ID",
    "PLAYER",
    "COUNTRY",
    "SINGLES_WON",
    "SINGLES_LOST",
    "MATCHES_PLAYED",
    "WIN_PCT",
    "SINGLES_TITLES",
    "DOUBLES_TITLES",
    "PRIZE_MONEY_USD",
]


def _extract_stat_values(stats_payload: dict) -> dict:
    """Flatten the general season stats returned by ESPN."""
    values = {column: None for column in STAT_NAME_MAP.values()}

    categories = stats_payload.get("splits", {}).get("categories", [])
    for category in categories:
        for stat in category.get("stats", []):
            mapped_name = STAT_NAME_MAP.get(stat.get("name"))
            if mapped_name:
                values[mapped_name] = stat.get("value")

    return values


def get_tennis_stats(
    tours: tuple[str, ...] = DEFAULT_TOURS,
    top_n: int | None = 20,
    limit: int | None = None,
) -> pd.DataFrame:
    """
    Fetch season-to-date tennis stats for the current top-ranked players.

    Returns a DataFrame with record, title, and prize-money fields.
    """
    rows = []
    row_limit = limit if limit is not None else top_n

    for tour in normalize_tours(tours):
        ranking_payload = _get_ranking_payload(tour_slug(tour))
        ranks = ranking_payload.get("ranks", [])
        if row_limit is not None:
            ranks = ranks[:row_limit]

        for rank_entry in ranks:
            athlete = _get_athlete_payload(rank_entry["athlete"]["$ref"])
            stats_ref = athlete.get("statistics", {}).get("$ref")
            stats_payload = fetch_json(normalize_ref(stats_ref)) if stats_ref else {}
            stat_values = _extract_stat_values(stats_payload)

            singles_won = stat_values.get("SINGLES_WON") or 0
            singles_lost = stat_values.get("SINGLES_LOST") or 0
            matches_played = singles_won + singles_lost
            win_pct = singles_won / matches_played if matches_played else None

            rows.append(
                {
                    "TOUR": TOUR_LABELS.get(tour, tour),
                    "RANK": rank_entry.get("current"),
                    "PLAYER_ID": str(athlete.get("id")) if athlete.get("id") is not None else None,
                    "PLAYER": athlete.get("displayName"),
                    "COUNTRY": athlete.get("citizenshipCountry", {}).get("abbreviation"),
                    "SINGLES_WON": singles_won,
                    "SINGLES_LOST": singles_lost,
                    "MATCHES_PLAYED": matches_played,
                    "WIN_PCT": win_pct,
                    "SINGLES_TITLES": stat_values.get("SINGLES_TITLES"),
                    "DOUBLES_TITLES": stat_values.get("DOUBLES_TITLES"),
                    "PRIZE_MONEY_USD": stat_values.get("PRIZE_MONEY_USD"),
                }
            )

    if not rows:
        return pd.DataFrame(columns=STAT_COLUMNS)

    df = pd.DataFrame(rows)
    return df.sort_values(["TOUR", "RANK", "PLAYER"]).reset_index(drop=True)


def get_tennis_player_stats(
    tours: tuple[str, ...] = DEFAULT_TOURS,
    top_n: int | None = 20,
    limit: int | None = None,
) -> pd.DataFrame:
    """Backward-compatible alias for the tennis stats fetcher."""
    return get_tennis_stats(tours=tours, top_n=top_n, limit=limit)

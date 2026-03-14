"""
Helpers for EPL team normalization and match IDs.
"""

import re
from datetime import date, datetime

from .constants import MATCH_KEY_PREFIX, TEAM_ALIASES, TEAM_IDS
from .types import MatchDateLike, MatchIdentity, MatchKey

NORMALIZE_PATTERN = re.compile(r"[^a-z0-9]+")


def _normalize_key(value: str) -> str:
    cleaned = value.strip().lower()
    cleaned = cleaned.replace("&", " and ")
    cleaned = cleaned.replace(".", "")
    cleaned = cleaned.replace("'", "")
    cleaned = cleaned.replace("’", "")
    cleaned = NORMALIZE_PATTERN.sub(" ", cleaned)
    return cleaned.strip()


def _build_team_lookup() -> dict[str, str]:
    lookup: dict[str, str] = {}

    for canonical_name, aliases in TEAM_ALIASES.items():
        for alias in aliases:
            normalized_alias = _normalize_key(alias)
            existing_name = lookup.get(normalized_alias)

            if existing_name and existing_name != canonical_name:
                raise ValueError(f"Duplicate EPL team alias: {alias}")

            lookup[normalized_alias] = canonical_name

    return lookup


TEAM_LOOKUP = _build_team_lookup()


def normalize_team_name(team_name: str) -> str:
    """
    Normalize an EPL team name or alias to the canonical team name.
    """
    if not isinstance(team_name, str):
        raise TypeError("Team name must be a string")

    normalized_name = _normalize_key(team_name)

    if not normalized_name:
        raise ValueError("Team name is required")

    try:
        return TEAM_LOOKUP[normalized_name]
    except KeyError as exc:
        raise ValueError(f"Unknown EPL team name: {team_name}") from exc


def get_team_id(team_name: str) -> str:
    """
    Return the stable team ID for a canonical team name or alias.
    """
    canonical_name = normalize_team_name(team_name)
    return TEAM_IDS[canonical_name]


def normalize_match_date(match_date: MatchDateLike) -> str:
    """
    Normalize a match date to ISO format (YYYY-MM-DD).
    """
    if isinstance(match_date, datetime):
        return match_date.date().isoformat()

    if isinstance(match_date, date):
        return match_date.isoformat()

    if isinstance(match_date, str):
        value = match_date.strip()

        if not value:
            raise ValueError("Match date is required")

        iso_value = value.replace("Z", "+00:00")

        try:
            return datetime.fromisoformat(iso_value).date().isoformat()
        except ValueError:
            pass

        for fmt in ("%Y/%m/%d", "%d/%m/%Y", "%d-%m-%Y"):
            try:
                return datetime.strptime(value, fmt).date().isoformat()
            except ValueError:
                continue

        raise ValueError(f"Unsupported match date format: {match_date}")

    raise TypeError("Match date must be a date, datetime, or string")


def build_match_identity(
    home_team: str,
    away_team: str,
    match_date: MatchDateLike,
) -> MatchIdentity:
    """
    Build a normalized match identity from home team, away team, and date.
    """
    normalized_home = normalize_team_name(home_team)
    normalized_away = normalize_team_name(away_team)

    if normalized_home == normalized_away:
        raise ValueError("Home and away teams must be different")

    return MatchIdentity(
        match_date=normalize_match_date(match_date),
        home_team=normalized_home,
        away_team=normalized_away,
    )


def build_match_key(
    home_team: str,
    away_team: str,
    match_date: MatchDateLike,
) -> MatchKey:
    """
    Build a deterministic EPL match key.
    """
    identity = build_match_identity(
        home_team=home_team,
        away_team=away_team,
        match_date=match_date,
    )
    home_team_id = TEAM_IDS[identity.home_team]
    away_team_id = TEAM_IDS[identity.away_team]
    return f"{MATCH_KEY_PREFIX}__{identity.match_date}__{home_team_id}__{away_team_id}"

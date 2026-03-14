"""
Core EPL domain helpers.
"""

from .constants import CANONICAL_TEAMS, MATCH_KEY_PREFIX, TEAM_ALIASES, TEAM_IDS
from .helpers import (
    build_match_identity,
    build_match_key,
    get_team_id,
    normalize_match_date,
    normalize_team_name,
)
from .types import MatchDateLike, MatchIdentity, MatchKey

__all__ = [
    "CANONICAL_TEAMS",
    "MATCH_KEY_PREFIX",
    "TEAM_ALIASES",
    "TEAM_IDS",
    "MatchDateLike",
    "MatchIdentity",
    "MatchKey",
    "build_match_identity",
    "build_match_key",
    "get_team_id",
    "normalize_match_date",
    "normalize_team_name",
]

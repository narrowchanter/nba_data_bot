"""
Common types for EPL domain helpers.
"""

from dataclasses import dataclass
from datetime import date, datetime
from typing import TypeAlias

CanonicalTeamName: TypeAlias = str
MatchDateLike: TypeAlias = str | date | datetime
MatchKey: TypeAlias = str
TeamAliasGroups: TypeAlias = dict[CanonicalTeamName, tuple[str, ...]]
TeamIdMap: TypeAlias = dict[CanonicalTeamName, str]


@dataclass(frozen=True)
class MatchIdentity:
    match_date: str
    home_team: CanonicalTeamName
    away_team: CanonicalTeamName

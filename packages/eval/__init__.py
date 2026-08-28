"""Defend eval — time/entity split, Brake (Plan 12). Champion fit is Phase C."""

from packages.eval.brake import POLICY_ACTIONS, BrakeDecision, brake
from packages.eval.fit import fit_champion, score_run
from packages.eval.split import SPLIT_ONLY_COLUMNS, assign_folds, build_matrix

__all__ = [
    "POLICY_ACTIONS",
    "BrakeDecision",
    "SPLIT_ONLY_COLUMNS",
    "assign_folds",
    "brake",
    "build_matrix",
    "fit_champion",
    "score_run",
]

"""Defend eval — time/entity split, Brake (Plan 12). Champion fit is Phase C."""

from packages.eval.brake import POLICY_ACTIONS, BrakeDecision, brake
from packages.eval.fit import fit_champion, score_run
from packages.eval.split import (
    SPLIT_ONLY_COLUMNS,
    assert_fold_n_pos,
    assign_folds,
    build_matrix,
    inner_folds_from_train,
    split_inner_val_ab,
)

__all__ = [
    "POLICY_ACTIONS",
    "BrakeDecision",
    "SPLIT_ONLY_COLUMNS",
    "assign_folds",
    "brake",
    "build_matrix",
    "fit_champion",
    "inner_folds_from_train",
    "score_run",
]

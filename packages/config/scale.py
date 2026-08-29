"""Production reference scale configuration (Phase 4).

Single source of truth for frozen run_ids, seeds, and population scale.
"""

SCALE_FULLMIX_RUN_ID = "make-scale-fullmix"
SCALE_GTEST_RUN_ID = "make-gtest"
SCALE_GDEV_RUN_ID = "make-gdev"
SCALE_GCONFIRM_RUN_ID = "make-gconfirm"

SCALE_TRAIN_SEED = 42
SCALE_GTEST_SEED = 43
SCALE_GDEV_SEED = 44
SCALE_CONFIRM_SEED = 45

SCALE_N_CUSTOMERS = 2400
SCALE_N_MERCHANTS = 120
SCALE_SIM_DAYS = 90

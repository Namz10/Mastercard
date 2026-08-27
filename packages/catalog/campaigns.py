"""Generate canary_mode campaign pins (Plan 01 §9, FinalIdentify Step 10)."""

from dataclasses import dataclass


@dataclass(frozen=True)
class CanaryCampaign:
    campaign_id: str
    name: str
    vector_ids: tuple[str, ...]
    lifecycle_stages: tuple[str, ...]
    primary_vector_id: str


FINCEN_ALERT004_CAMPAIGN = CanaryCampaign(
    campaign_id="fincen-fin-2024-alert004",
    name="FinCEN FIN-2024-Alert004 composite chain",
    vector_ids=(
        "t09-deepfake-vkyc",
        "t11-identity-farming",
        "t13-upi-impersonation-app",
        "t02-mule-fan-out",
    ),
    lifecycle_stages=(
        "onboarding_kyc",
        "account_access_ato",
        "payment_initiation",
        "disbursement_mule",
    ),
    primary_vector_id="t13-upi-impersonation-app",
)

CAMPAIGNS: dict[str, CanaryCampaign] = {
    FINCEN_ALERT004_CAMPAIGN.campaign_id: FINCEN_ALERT004_CAMPAIGN,
}

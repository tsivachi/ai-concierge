"""Personalization layer (FR-013): called only *after* deterministic ranking
has already finalized a NextBestActionRecord — decisioning/nba.py itself
never calls the LLM (Constitution Principle I). Personalization is
additive-only: it produces wording, never changes the underlying priority,
tie_break_rank, or reason_codes."""

ACTION_LABELS = {
    "ACTIVATION_FAILURE": "resolve your device activation failure",
    "NUMBER_TRANSFER_FAILURE": "resolve your number transfer failure",
    "NETWORK_FAILURE": "resolve your network validation failure",
    "REQUIRED_SECURITY_INCOMPLETE": "finish setting up your account security",
    "BILLING_RENEWAL_READINESS": "review your upcoming bill or renewal",
    "AUTOPAY_AUTO_RECHARGE_GAP": "set up AutoPay or auto-recharge",
    "APP_GAP": "download the mobile app",
    "VOICEMAIL_GAP": "set up your voicemail",
    "PROTECTION_DECISION_GAP": "decide on device protection",
    "PREMIUM_FEATURE": "check out an eligible premium feature",
}


def personalize_nba_message(llm_provider, action_code: str) -> str:
    label = ACTION_LABELS.get(action_code, action_code)
    return llm_provider.generate("", {"kind": "nba_message", "label": label})


def personalize_billing_explanation(llm_provider, postpaid_estimate: dict | None, prepaid_renewal: dict | None) -> str:
    """Called only after decisioning/billing.py has already computed the
    estimate/readiness figures (T076-T077) — the LLM explains those already-
    finalized values, it never calculates them (FR-025, FR-026)."""
    if postpaid_estimate is not None:
        estimate_text = f"total estimate ${postpaid_estimate['total_estimate']}"
        return llm_provider.generate("", {"kind": "billing_explanation", "estimate": estimate_text})
    if prepaid_renewal is not None:
        readiness = "ready" if prepaid_renewal["renewal_ready"] else "not yet ready"
        estimate_text = f"balance ${prepaid_renewal['balance']}, renewal {readiness}"
        return llm_provider.generate("", {"kind": "billing_explanation", "estimate": estimate_text})
    return "No billing or renewal information is available for this line yet."

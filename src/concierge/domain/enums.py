from enum import Enum


class ActivityStatus(str, Enum):
    NOT_STARTED = "NOT_STARTED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    NOT_APPLICABLE = "NOT_APPLICABLE"


TERMINAL_ACTIVITY_STATUSES = (
    ActivityStatus.COMPLETED,
    ActivityStatus.NOT_APPLICABLE,
)


class RequirementClass(str, Enum):
    REQUIRED = "REQUIRED"
    RECOMMENDED = "RECOMMENDED"
    OPTIONAL = "OPTIONAL"


class PlanType(str, Enum):
    POSTPAID = "POSTPAID"
    PREPAID = "PREPAID"


class ActivityScope(str, Enum):
    ACCOUNT = "ACCOUNT"
    LINE = "LINE"


class HealthBand(str, Enum):
    GREEN = "GREEN"
    YELLOW = "YELLOW"
    RED = "RED"


def health_band_for_score(score: int) -> HealthBand:
    """FR-017: GREEN 75-100, YELLOW 40-74, RED 0-39."""
    if score >= 75:
        return HealthBand.GREEN
    if score >= 40:
        return HealthBand.YELLOW
    return HealthBand.RED


class JourneyStatus(str, Enum):
    ACTIVE = "ACTIVE"
    COMPLETE = "COMPLETE"
    EXPIRED = "EXPIRED"


class LineJourneyStatus(str, Enum):
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETE = "COMPLETE"


class EventType(str, Enum):
    """FR-006: the 18 supported event types."""

    ORDER_COMPLETED = "OrderCompleted"
    DEVICE_DELIVERED = "DeviceDelivered"
    DEVICE_ACTIVATION_STARTED = "DeviceActivationStarted"
    DEVICE_ACTIVATION_COMPLETED = "DeviceActivationCompleted"
    DEVICE_ACTIVATION_FAILED = "DeviceActivationFailed"
    NUMBER_TRANSFER_REQUESTED = "NumberTransferRequested"
    NUMBER_TRANSFER_PENDING = "NumberTransferPending"
    NUMBER_TRANSFER_COMPLETED = "NumberTransferCompleted"
    NUMBER_TRANSFER_FAILED = "NumberTransferFailed"
    CUSTOMER_LOGGED_IN = "CustomerLoggedIn"
    MOBILE_APP_DOWNLOADED = "MobileAppDownloaded"
    VOICEMAIL_CONFIGURED = "VoicemailConfigured"
    AUTOPAY_ENABLED = "AutoPayEnabled"
    AUTO_RECHARGE_ENABLED = "AutoRechargeEnabled"
    HELP_ARTICLE_VIEWED = "HelpArticleViewed"
    SETUP_ABANDONED = "SetupAbandoned"
    CHAT_STARTED = "ChatStarted"
    SUPPORT_CASE_CREATED = "SupportCaseCreated"

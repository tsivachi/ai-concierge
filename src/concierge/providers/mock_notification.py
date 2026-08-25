"""Deterministic mock for NotificationProvider (FR-029, FR-030). Supports a
channel abstraction (push/SMS/email/in-app) without any real integration —
"sending" is simulated and returns a deterministic receipt; actual delivery
bookkeeping (OutreachAttempt rows) is the decisioning layer's job, not this
provider's."""

import hashlib


class MockNotificationProvider:
    SUPPORTED_CHANNELS = ("push", "sms", "email", "in_app")

    def send(self, customer_id: str, channel: str, message: str) -> dict:
        if channel not in self.SUPPORTED_CHANNELS:
            raise ValueError(f"unsupported channel: {channel}")
        message_id = hashlib.sha256(f"{customer_id}:{channel}:{message}".encode()).hexdigest()[:16]
        return {"status": "sent", "channel": channel, "customer_id": customer_id, "message_id": message_id}

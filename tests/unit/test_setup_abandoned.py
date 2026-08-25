from datetime import datetime, timedelta, timezone

from concierge.decisioning.friction import FrictionEvent, PORT_PENDING_THRESHOLD_DAYS, detect_friction

NOW = datetime(2026, 8, 24, tzinfo=timezone.utc)


def test_setup_abandoned_event_flags_the_activity_code():
    events = [FrictionEvent("SetupAbandoned", NOW, activity_code="APP_ADOPTION")]
    flags = detect_friction(events, NOW)
    assert flags.setup_abandoned_activity_codes == frozenset({"APP_ADOPTION"})


def test_multiple_abandoned_activities_all_tracked():
    events = [
        FrictionEvent("SetupAbandoned", NOW, activity_code="APP_ADOPTION"),
        FrictionEvent("SetupAbandoned", NOW, activity_code="VOICEMAIL_SETUP"),
    ]
    flags = detect_friction(events, NOW)
    assert flags.setup_abandoned_activity_codes == frozenset({"APP_ADOPTION", "VOICEMAIL_SETUP"})


def test_no_setup_abandoned_events_yields_empty_set():
    flags = detect_friction([], NOW)
    assert flags.setup_abandoned_activity_codes == frozenset()


def test_single_help_article_view_is_not_repeated():
    events = [FrictionEvent("HelpArticleViewed", NOW, topic="activation")]
    flags = detect_friction(events, NOW)
    assert flags.repeated_help_visit is False


def test_two_help_article_views_on_same_topic_is_repeated():
    events = [
        FrictionEvent("HelpArticleViewed", NOW, topic="activation"),
        FrictionEvent("HelpArticleViewed", NOW, topic="activation"),
    ]
    flags = detect_friction(events, NOW)
    assert flags.repeated_help_visit is True


def test_two_help_article_views_on_different_topics_is_not_repeated():
    events = [
        FrictionEvent("HelpArticleViewed", NOW, topic="activation"),
        FrictionEvent("HelpArticleViewed", NOW, topic="billing"),
    ]
    flags = detect_friction(events, NOW)
    assert flags.repeated_help_visit is False


def test_two_chats_on_same_topic_is_unresolved_repeated_chat():
    events = [
        FrictionEvent("ChatStarted", NOW, topic="porting"),
        FrictionEvent("ChatStarted", NOW, topic="porting"),
    ]
    flags = detect_friction(events, NOW)
    assert flags.unresolved_repeated_chat is True


def test_port_pending_past_threshold_flags_too_long():
    pending_at = NOW - timedelta(days=PORT_PENDING_THRESHOLD_DAYS)
    events = [FrictionEvent("NumberTransferPending", pending_at)]
    flags = detect_friction(events, NOW)
    assert flags.port_pending_too_long is True


def test_port_pending_before_threshold_does_not_flag():
    pending_at = NOW - timedelta(days=PORT_PENDING_THRESHOLD_DAYS - 1)
    events = [FrictionEvent("NumberTransferPending", pending_at)]
    flags = detect_friction(events, NOW)
    assert flags.port_pending_too_long is False


def test_port_pending_resolved_by_completion_clears_flag():
    pending_at = NOW - timedelta(days=PORT_PENDING_THRESHOLD_DAYS + 2)
    events = [
        FrictionEvent("NumberTransferPending", pending_at),
        FrictionEvent("NumberTransferCompleted", NOW),
    ]
    flags = detect_friction(events, NOW)
    assert flags.port_pending_too_long is False

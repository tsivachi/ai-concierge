from concierge.conversation.engine import (
    SUPPORTED_ACTION_CODES,
    requests_unsupported_action,
)
from concierge.decisioning.nba import BASE_PRIORITY


def test_supported_action_codes_match_fr011_catalog():
    assert SUPPORTED_ACTION_CODES == frozenset(BASE_PRIORITY.keys())


def test_cancel_line_request_is_flagged_unsupported():
    assert requests_unsupported_action("please cancel my line") is True


def test_refund_request_is_flagged_unsupported():
    assert requests_unsupported_action("can I get a refund for last month?") is True


def test_plan_change_request_is_flagged_unsupported():
    assert requests_unsupported_action("I want to upgrade my plan") is True


def test_ordinary_troubleshooting_question_is_not_flagged():
    assert requests_unsupported_action("why is my activation still pending?") is False


def test_generic_help_question_is_not_flagged():
    assert requests_unsupported_action("how do I set up voicemail?") is False

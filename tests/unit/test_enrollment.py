"""FR-001/FR-002/FR-003: journey enrollment on OrderCompleted."""

from datetime import datetime, timezone

from concierge.journey.enrollment import enroll_line_on_order_completed
from concierge.persistence.repositories import JourneyRepository


def test_single_line_postpaid_with_port_enrollment(db_session):
    now = datetime.now(timezone.utc)
    journey = enroll_line_on_order_completed(
        db_session,
        account_id="acct-1",
        customer_id="cust-1",
        line_id="line-1",
        plan_type="POSTPAID",
        number_port_requested=True,
        occurred_at=now,
    )

    journey_repo = JourneyRepository(db_session)
    assert journey.account_id == "acct-1"
    assert journey.status == "ACTIVE"

    instances = journey_repo.list_activity_instances_for_journey(journey.journey_id)
    by_code = {i.activity_code: i for i in instances if i.line_id == "line-1"}
    assert by_code["NUMBER_TRANSFER"].status == "NOT_STARTED"
    assert by_code["NUMBER_TRANSFER"].requirement_class == "REQUIRED"
    assert by_code["SIM_ESIM_ACTIVATION"].status == "NOT_STARTED"

    account_activities = {i.activity_code for i in instances if i.line_id is None}
    assert "ACCOUNT_SECURITY" in account_activities


def test_prepaid_byod_no_port_marks_number_transfer_not_applicable(db_session):
    now = datetime.now(timezone.utc)
    journey = enroll_line_on_order_completed(
        db_session,
        account_id="acct-2",
        customer_id="cust-2",
        line_id="line-2",
        plan_type="PREPAID",
        number_port_requested=False,
        occurred_at=now,
    )

    journey_repo = JourneyRepository(db_session)
    instance = journey_repo.get_activity_instance(journey.journey_id, "line-2", "NUMBER_TRANSFER")
    assert instance.status == "NOT_APPLICABLE"

    # Prepaid-only recommended activities are present; postpaid-only ones are not.
    instances = journey_repo.list_activity_instances_for_journey(journey.journey_id)
    codes = {i.activity_code for i in instances if i.line_id == "line-2"}
    assert "AUTO_RECHARGE_SETUP" in codes
    assert "AUTOPAY_PAYMENT_SETUP" not in codes


def test_multi_line_postpaid_enrollment_shares_one_journey_and_account_security(db_session):
    now = datetime.now(timezone.utc)
    journey1 = enroll_line_on_order_completed(
        db_session, account_id="acct-3", customer_id="cust-3", line_id="line-3a",
        plan_type="POSTPAID", number_port_requested=False, occurred_at=now,
    )
    journey2 = enroll_line_on_order_completed(
        db_session, account_id="acct-3", customer_id="cust-3", line_id="line-3b",
        plan_type="POSTPAID", number_port_requested=True, occurred_at=now,
    )

    assert journey1.journey_id == journey2.journey_id

    journey_repo = JourneyRepository(db_session)
    instances = journey_repo.list_activity_instances_for_journey(journey1.journey_id)
    account_security_rows = [i for i in instances if i.activity_code == "ACCOUNT_SECURITY"]
    assert len(account_security_rows) == 1  # instantiated once per journey, not once per line

    line_states = journey_repo.list_line_states_for_journey(journey1.journey_id)
    assert {s.line_id for s in line_states} == {"line-3a", "line-3b"}


def test_second_order_on_account_with_active_journey_attaches_not_duplicates(db_session):
    """spec.md Assumptions: at most one active journey per account."""
    now = datetime.now(timezone.utc)
    first = enroll_line_on_order_completed(
        db_session, account_id="acct-4", customer_id="cust-4", line_id="line-4a",
        plan_type="POSTPAID", number_port_requested=False, occurred_at=now,
    )
    second = enroll_line_on_order_completed(
        db_session, account_id="acct-4", customer_id="cust-4", line_id="line-4b",
        plan_type="POSTPAID", number_port_requested=False, occurred_at=now,
    )
    assert first.journey_id == second.journey_id


def test_re_enrolling_an_already_enrolled_line_is_a_safe_no_op(db_session):
    now = datetime.now(timezone.utc)
    journey_repo = JourneyRepository(db_session)

    enroll_line_on_order_completed(
        db_session, account_id="acct-5", customer_id="cust-5", line_id="line-5",
        plan_type="POSTPAID", number_port_requested=False, occurred_at=now,
    )
    before_count = len(journey_repo.list_activity_instances_for_journey(
        journey_repo.get_active_journey_for_account("acct-5").journey_id
    ))

    enroll_line_on_order_completed(
        db_session, account_id="acct-5", customer_id="cust-5", line_id="line-5",
        plan_type="POSTPAID", number_port_requested=False, occurred_at=now,
    )
    after_count = len(journey_repo.list_activity_instances_for_journey(
        journey_repo.get_active_journey_for_account("acct-5").journey_id
    ))

    assert before_count == after_count

import pytest
from sitewatch.domain import Detection, EventRules, EventState
from sitewatch.schemas import SourceUpdate


def test_stationary_presence_does_not_depend_on_motion():
    rules = EventRules()
    assert rules.step(0, False, 1) == (False, False)
    assert rules.step(0.5, False, 1) == (True, False)
    for now in range(1, 12):
        assert not rules.step(now, False, 1)[1]
    assert rules.state.person_confirmed
    assert rules.state.classify() == "person_detected"


def test_motion_only_can_close_without_claiming_false_alarm():
    rules = EventRules()
    rules.step(0, True, 0)
    assert rules.step(0.5, True, 0)[0]
    for now in (1, 2, 3, 4, 5):
        assert not rules.step(now, False, 0)[1]
    assert rules.step(5.5, False, 0)[1]
    assert rules.state.classify() == "no_person_detected"


def test_brief_false_detection_does_not_confirm_presence():
    rules = EventRules()
    rules.step(0, True, 1)
    rules.step(0.5, True, 0)
    for now in (1, 2, 3, 4, 5, 6):
        rules.step(now, False, 0)
    assert not rules.state.person_confirmed


def test_long_gaps_and_failure_are_never_negative():
    state = EventState(0, 0)
    for now in (0, 0.5, 4):
        state.sample(now, 0, False)
    assert state.classify() == "inconclusive"
    state.max_gap = 0
    state.failed = True
    assert state.classify() == "inconclusive"
    state.failed = False
    assert state.classify(interrupted=True) == "inconclusive"


def test_positive_evidence_survives_interruption():
    state = EventState(0, 0, person_confirmed=True, failed=True)
    assert state.classify(interrupted=True) == "person_detected"


def test_peak_count_is_not_a_unique_visitor_count():
    rules = EventRules()
    rules.step(0, False, 2)
    rules.step(0.4, False, 2)
    rules.step(1, False, 1)
    rules.step(2, False, 3)
    assert rules.state.peak_people == 3


def test_region_uses_bottom_center_including_boundary():
    assert Detection(0.9, (0.1, 0.1, 0.5, 0.8)).in_region((0.3, 0.5, 0.2, 0.3))
    assert not Detection(0.9, (0.5, 0.1, 0.9, 0.8)).in_region((0.3, 0.5, 0.2, 0.3))


@pytest.mark.parametrize(
    "roi", [(-0.1, 0, 1, 1), (0, 0, 0, 1), (0.8, 0.8, 0.4, 0.4), (0, 0, float("nan"), 1)]
)
def test_invalid_regions_are_rejected(roi):
    with pytest.raises(ValueError):
        SourceUpdate(name="test", camera_index=0, roi=roi, confidence=0.5, motion_threshold=0.01)


def test_reset_prevents_stale_confirmation_from_opening_next_event():
    rules = EventRules()
    rules.step(0, False, 1)
    rules.step(0.1, False, 1)
    rules.reset()
    assert rules.step(0.2, False, 1) == (False, False)

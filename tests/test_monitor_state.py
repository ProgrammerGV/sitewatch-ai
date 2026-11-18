import pytest
from pydantic import ValidationError
from sitewatch.monitor_state import MonitorPhase, MonitorStatus


def test_unknown_states_and_misspelled_fields_are_rejected():
    status = MonitorStatus()
    with pytest.raises(ValidationError):
        status.with_changes(state="runing")
    with pytest.raises(ValidationError):
        status.with_changes(people_in_reigon=1)
    with pytest.raises(ValidationError):
        status.with_changes(people=-1)


def test_state_updates_preserve_previous_snapshot_and_wire_values():
    idle = MonitorStatus()
    running = idle.with_changes(state=MonitorPhase.RUNNING, people=2)
    assert idle.state == MonitorPhase.IDLE
    assert running.model_dump(mode="json")["state"] == "running"
    assert running.people == 2

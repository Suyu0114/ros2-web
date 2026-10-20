import math

import pytest

from app.convert import navsatfix_to_fix
from tests.helpers import fake_navsatfix


def test_converts_fields_and_stamp_to_epoch_ms():
    fix = navsatfix_to_fix(fake_navsatfix(lat=22.6, lon=120.2, alt=1.5), seq=7)
    assert fix is not None
    assert fix.model_dump() == {
        "seq": 7,
        "t": 1_760_000_000_250,
        "lat": 22.6,
        "lon": 120.2,
        "alt": 1.5,
        "status": 0,
        "frame_id": "gps",
    }


@pytest.mark.parametrize("status", [-1, -2], ids=["STATUS_NO_FIX", "STATUS_UNKNOWN"])
def test_drops_messages_without_a_valid_fix(status):
    assert navsatfix_to_fix(fake_navsatfix(status=status), seq=1) is None


@pytest.mark.parametrize("field", ["lat", "lon"])
def test_drops_non_finite_coordinates(field):
    assert navsatfix_to_fix(fake_navsatfix(**{field: math.nan}), seq=1) is None


def test_unknown_altitude_becomes_null():
    fix = navsatfix_to_fix(fake_navsatfix(alt=math.nan), seq=1)
    assert fix is not None and fix.alt is None


def test_real_navsatfix_message():
    msg_module = pytest.importorskip("sensor_msgs.msg", reason="needs ROS 2 (runs in the backend image)")
    msg = msg_module.NavSatFix()
    msg.header.stamp.sec, msg.header.stamp.nanosec = 1_760_000_000, 999_999_999
    msg.header.frame_id = "gps"
    msg.status.status = msg_module.NavSatStatus.STATUS_FIX
    msg.latitude, msg.longitude, msg.altitude = 22.6166, 120.279, 0.0
    fix = navsatfix_to_fix(msg, seq=1)
    assert fix is not None
    assert (fix.t, fix.lat, fix.lon) == (1_760_000_000_999, 22.6166, 120.279)

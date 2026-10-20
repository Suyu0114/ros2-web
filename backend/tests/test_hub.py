from app.hub import TelemetryHub
from tests.helpers import make_fix


async def test_history_is_bounded_and_limit_returns_latest():
    hub = TelemetryHub(history_size=3, client_queue_size=10)
    for seq in range(1, 6):
        hub.publish(make_fix(seq))
    assert [f.seq for f in hub.history()] == [3, 4, 5]
    assert [f.seq for f in hub.history(limit=2)] == [4, 5]
    assert hub.fixes_received == 5


async def test_subscriber_gets_snapshot_then_only_new_fixes():
    hub = TelemetryHub(history_size=10, client_queue_size=10)
    hub.publish(make_fix(1))
    with hub.subscribe() as (snapshot, queue):
        hub.publish(make_fix(2))
        assert [f.seq for f in snapshot] == [1]
        assert (await queue.get()).seq == 2
        assert queue.empty()
        assert hub.client_count == 1
    assert hub.client_count == 0


async def test_slow_client_drops_oldest_without_blocking_others():
    hub = TelemetryHub(history_size=10, client_queue_size=2)
    with hub.subscribe() as (_, slow), hub.subscribe() as (_, fast):
        for seq in range(1, 4):
            hub.publish(make_fix(seq))
            if seq < 3:
                assert (await fast.get()).seq == seq
        assert [slow.get_nowait().seq for _ in range(slow.qsize())] == [2, 3]
        assert (await fast.get()).seq == 3
    assert hub.dropped == 1


async def test_each_hub_has_its_own_session():
    assert TelemetryHub(1, 1).session != TelemetryHub(1, 1).session


async def test_last_fix_age():
    hub = TelemetryHub(history_size=1, client_queue_size=1)
    assert hub.last_fix_age_s is None
    hub.publish(make_fix(1))
    assert 0 <= hub.last_fix_age_s < 1

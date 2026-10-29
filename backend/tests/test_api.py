import time

import pytest
from fastapi import WebSocketDisconnect
from fastapi.testclient import TestClient

from app.main import app
from app.settings import get_settings
from tests.helpers import make_fix


@pytest.fixture
def client(no_ros):
    with TestClient(app) as c:  # 進入 context 才會跑 lifespan（建立 hub）
        yield c


def publish(client: TestClient, seq: int) -> None:
    # hub 只能在 app 的 event loop 執行緒呼叫，就像 ROS 執行緒用 call_soon_threadsafe 一樣
    client.portal.call(app.state.hub.publish, make_fix(seq))


def test_healthz_reports_degraded_without_ros(client):
    body = client.get("/api/healthz").json()
    assert body["status"] == "degraded"
    assert body["ros_enabled"] is False
    assert body["fixes_received"] == 0


def test_track_returns_history_with_limit(client):
    for seq in range(1, 8):
        publish(client, seq)
    assert [p["seq"] for p in client.get("/api/track").json()] == [3, 4, 5, 6, 7]  # history_size=5
    assert [p["seq"] for p in client.get("/api/track", params={"limit": 2}).json()] == [6, 7]
    assert client.get("/api/track", params={"limit": 0}).status_code == 422


def test_websocket_sends_snapshot_then_live_fixes(client):
    publish(client, 1)
    publish(client, 2)
    with client.websocket_connect("/ws/gps") as ws:
        snapshot = ws.receive_json()
        assert snapshot["type"] == "snapshot"
        assert snapshot["session"] == app.state.hub.session
        assert [p["seq"] for p in snapshot["points"]] == [1, 2]

        publish(client, 3)
        message = ws.receive_json()
        assert message["type"] == "fix"
        assert message["data"]["seq"] == 3
        assert set(message["data"]) == {"seq", "t", "lat", "lon", "alt", "status", "frame_id"}


def test_websocket_rejects_cross_site_origin(client):
    with pytest.raises(WebSocketDisconnect) as excinfo:
        with client.websocket_connect("/ws/gps", headers={"origin": "https://evil.example"}):
            pass
    assert excinfo.value.code == 1008
    assert client.get("/api/healthz").json()["clients"] == 0


def test_websocket_accepts_same_origin_and_non_browser_clients(client):
    # TestClient 的 Host 是 testserver；沒有 Origin 的是非瀏覽器 client
    for headers in ({"origin": "http://testserver"}, {"origin": "HTTP://TestServer"}, {}):
        with client.websocket_connect("/ws/gps", headers=headers) as ws:
            assert ws.receive_json()["type"] == "snapshot"


def test_websocket_accepts_extra_allowed_origins(no_ros, monkeypatch):
    monkeypatch.setenv("BRIDGE_ALLOWED_ORIGINS", "https://gcs.example, http://10.0.0.5:8080")
    get_settings.cache_clear()
    with TestClient(app) as client:
        for origin in ("https://gcs.example", "http://10.0.0.5:8080", "http://testserver"):
            with client.websocket_connect("/ws/gps", headers={"origin": origin}) as ws:
                assert ws.receive_json()["type"] == "snapshot"
        with pytest.raises(WebSocketDisconnect):
            with client.websocket_connect("/ws/gps", headers={"origin": "http://10.0.0.5:9999"}):
                pass


def test_websocket_unsubscribes_on_disconnect(client):
    with client.websocket_connect("/ws/gps") as ws:
        ws.receive_json()
        assert client.get("/api/healthz").json()["clients"] == 1
    # 斷線後 hub 要移除這個 client；給 server 端一點時間處理 disconnect
    for _ in range(50):
        if client.get("/api/healthz").json()["clients"] == 0:
            break
        time.sleep(0.02)
    assert client.get("/api/healthz").json()["clients"] == 0

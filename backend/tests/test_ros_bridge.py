"""實際走一次 ROS 2：發佈 NavSatFix → RosBridge 的背景執行緒 → event loop 上的 hub。

需要 rclpy，只在 backend image 裡跑（CI 的 backend job）。
"""

import asyncio

import pytest

rclpy = pytest.importorskip("rclpy", reason="needs ROS 2 (runs in the backend image)")

from rclpy.qos import qos_profile_sensor_data  # noqa: E402
from sensor_msgs.msg import NavSatFix, NavSatStatus  # noqa: E402

from app.hub import TelemetryHub  # noqa: E402
from app.ros_bridge import RosBridge  # noqa: E402

TOPIC = "/test/gps/fix"


async def test_bridge_delivers_fixes_to_hub_on_event_loop():
    hub = TelemetryHub(history_size=100, client_queue_size=100)
    bridge = RosBridge(TOPIC, hub, asyncio.get_running_loop())
    bridge.start()
    node = rclpy.create_node("test_gps_publisher")
    try:
        publisher = node.create_publisher(NavSatFix, TOPIC, qos_profile_sensor_data)
        msg = NavSatFix()
        msg.header.frame_id = "gps"
        msg.status.status = NavSatStatus.STATUS_FIX  # Jazzy 的預設值是 STATUS_UNKNOWN（-2）
        msg.latitude, msg.longitude = 22.6166, 120.279

        no_fix = NavSatFix()
        no_fix.status.status = NavSatStatus.STATUS_NO_FIX  # bridge 應該丟掉

        for _ in range(100):  # 最多 10 秒，等 DDS discovery 完成
            publisher.publish(no_fix)
            publisher.publish(msg)
            await asyncio.sleep(0.1)
            if hub.fixes_received >= 3:
                break

        history = hub.history()
        assert len(history) >= 3
        assert all(f.lat == 22.6166 for f in history)
        assert [f.seq for f in history] == list(range(1, len(history) + 1))
    finally:
        node.destroy_node()
        bridge.stop()

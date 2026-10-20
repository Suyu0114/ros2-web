"""ROS 2 端：訂閱 /gps/fix，把轉好的 GpsFix 交給 asyncio 那一側的 TelemetryHub。"""

import asyncio
import threading
from collections.abc import Callable

import rclpy
from rclpy.executors import ExternalShutdownException, SingleThreadedExecutor
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from rclpy.signals import SignalHandlerOptions
from sensor_msgs.msg import NavSatFix

from app.convert import navsatfix_to_fix
from app.hub import TelemetryHub
from app.schemas import GpsFix


class GpsBridgeNode(Node):
    def __init__(self, topic: str, on_fix: Callable[[GpsFix], None]) -> None:
        super().__init__("gnss_web_bridge")
        self._on_fix = on_fix
        self._seq = 0
        # 與 publisher 的 SensorDataQoS 相容（best effort）
        self.create_subscription(NavSatFix, topic, self._on_message, qos_profile_sensor_data)
        self.get_logger().info(f"Subscribed to {topic}")

    def _on_message(self, msg: NavSatFix) -> None:
        fix = navsatfix_to_fix(msg, self._seq + 1)
        if fix is None:
            return
        self._seq = fix.seq
        self._on_fix(fix)


class RosBridge:
    """在背景執行緒跑 rclpy executor；callback 用 call_soon_threadsafe 交回 event loop。"""

    def __init__(self, topic: str, hub: TelemetryHub, loop: asyncio.AbstractEventLoop) -> None:
        self._topic = topic
        self._hub = hub
        self._loop = loop
        self._node: GpsBridgeNode | None = None
        self._executor: SingleThreadedExecutor | None = None
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        # 訊號交給 uvicorn 處理，docker stop 時才能走 lifespan 正常關閉
        rclpy.init(signal_handler_options=SignalHandlerOptions.NO)
        self._node = GpsBridgeNode(self._topic, self._deliver)
        self._executor = SingleThreadedExecutor()
        self._executor.add_node(self._node)
        self._thread = threading.Thread(target=self._spin, name="ros-spin", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        if self._executor is not None:
            self._executor.shutdown()
        if self._node is not None:
            self._node.destroy_node()
        rclpy.try_shutdown()
        if self._thread is not None:
            self._thread.join(timeout=2.0)

    def _deliver(self, fix: GpsFix) -> None:
        self._loop.call_soon_threadsafe(self._hub.publish, fix)

    def _spin(self) -> None:
        try:
            self._executor.spin()
        except ExternalShutdownException:
            pass

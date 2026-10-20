import pytest

from app.settings import get_settings


@pytest.fixture
def no_ros(monkeypatch):
    """關掉 ROS bridge，讓 API 測試不需要 rclpy。"""
    monkeypatch.setenv("BRIDGE_ROS_ENABLED", "false")
    monkeypatch.setenv("BRIDGE_HISTORY_SIZE", "5")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()

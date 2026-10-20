from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """環境變數設定，前綴 BRIDGE_（例如 BRIDGE_HISTORY_SIZE=3000）。"""

    model_config = SettingsConfigDict(env_prefix="BRIDGE_")

    ros_enabled: bool = True  # 測試時關掉，就不需要 rclpy
    gps_topic: str = "/gps/fix"
    history_size: int = 3000  # 保留的歷史點數；5Hz 下約 10 分鐘
    client_queue_size: int = 100  # 每個 WebSocket client 的待送佇列上限
    stale_after_s: float = 2.0  # 超過這麼久沒收到 fix，healthz 回報 degraded


@lru_cache
def get_settings() -> Settings:
    return Settings()

"""sensor_msgs/NavSatFix → GpsFix。

只靠屬性存取（duck typing），不 import ROS，所以沒有 rclpy 的環境也能測試。
"""

import math

from app.schemas import GpsFix

# sensor_msgs/NavSatStatus：status >= STATUS_FIX 才是有效定位。
# 小於它的是 STATUS_NO_FIX（-1）與 STATUS_UNKNOWN（-2，Jazzy 起為欄位預設值）。
STATUS_FIX = 0


def navsatfix_to_fix(msg, seq: int) -> GpsFix | None:
    """沒有有效定位，或經緯度不是有限數值時回傳 None（這種訊息不推給前端）。"""
    if msg.status.status < STATUS_FIX:
        return None
    lat, lon, alt = msg.latitude, msg.longitude, msg.altitude
    if not (math.isfinite(lat) and math.isfinite(lon)):
        return None
    stamp = msg.header.stamp
    return GpsFix(
        seq=seq,
        t=stamp.sec * 1000 + stamp.nanosec // 1_000_000,
        lat=lat,
        lon=lon,
        alt=alt if math.isfinite(alt) else None,
        status=msg.status.status,
        frame_id=msg.header.frame_id,
    )

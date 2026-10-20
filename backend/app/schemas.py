"""REST 與 WebSocket 對外的 JSON 格式。前端的 src/types.ts 與這裡保持一致。"""

from typing import Literal

from pydantic import BaseModel


class GpsFix(BaseModel):
    seq: int  # bridge 收到的第幾筆有效 fix，單調遞增；前端用來去重
    t: int  # header.stamp，epoch 毫秒
    lat: float
    lon: float
    alt: float | None  # NavSatFix 的 altitude 為 NaN 時是 null
    status: int  # NavSatStatus.status：0 FIX、1 SBAS_FIX、2 GBAS_FIX（只推送有效定位）
    frame_id: str


class SnapshotMessage(BaseModel):
    """連線後第一則訊息：目前保存的歷史軌跡。"""

    type: Literal["snapshot"] = "snapshot"
    # backend 每次啟動都不同。前端重連時據此判斷：同一個 session 用 snapshot 補上斷線期間的點；
    # 不同 session（backend 重啟、歷史清空、seq 從 1 重新編號）則保留畫面上已有的航跡
    session: str
    points: list[GpsFix]


class FixMessage(BaseModel):
    """之後每收到一筆 fix 推送一則。"""

    type: Literal["fix"] = "fix"
    data: GpsFix


class Health(BaseModel):
    status: Literal["ok", "degraded"]  # degraded：ROS 已停用，或太久沒收到 fix
    ros_enabled: bool
    fixes_received: int
    last_fix_age_s: float | None
    clients: int

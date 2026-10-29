import asyncio
from contextlib import asynccontextmanager
from typing import Annotated
from urllib.parse import urlsplit

import anyio
from fastapi import FastAPI, Query, Request, WebSocket, WebSocketDisconnect, status

from app.hub import TelemetryHub
from app.schemas import FixMessage, GpsFix, Health, SnapshotMessage
from app.settings import get_settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    hub = TelemetryHub(settings.history_size, settings.client_queue_size)
    app.state.hub = hub

    bridge = None
    if settings.ros_enabled:
        from app.ros_bridge import RosBridge  # 延後 import：關掉 ROS 時不需要 rclpy

        bridge = RosBridge(settings.gps_topic, hub, asyncio.get_running_loop())
        bridge.start()
    try:
        yield
    finally:
        if bridge is not None:
            bridge.stop()


app = FastAPI(
    title="GNSS Web Bridge",
    summary="ROS 2 /gps/fix → JSON over WebSocket",
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
    redoc_url=None,
    lifespan=lifespan,
)


@app.get("/api/healthz", response_model=Health)
def healthz(request: Request) -> Health:
    settings = get_settings()
    hub: TelemetryHub = request.app.state.hub
    age = hub.last_fix_age_s
    fresh = age is not None and age <= settings.stale_after_s
    return Health(
        status="ok" if settings.ros_enabled and fresh else "degraded",
        ros_enabled=settings.ros_enabled,
        fixes_received=hub.fixes_received,
        last_fix_age_s=age,
        clients=hub.client_count,
    )


@app.get("/api/track", response_model=list[GpsFix])
def track(
    request: Request,
    limit: Annotated[int | None, Query(ge=1, description="只回傳最新的 N 點")] = None,
) -> list[GpsFix]:
    return request.app.state.hub.history(limit)


def origin_allowed(websocket: WebSocket) -> bool:
    """防跨站 WebSocket 劫持（CSWSH）。

    瀏覽器的 WebSocket 不受同源政策限制：GCS 主機上開的任何網頁都能連進來讀船位，
    所以要自己檢查 Origin。同源（Origin 與 Host 相同）或列在 BRIDGE_ALLOWED_ORIGINS 才放行。
    瀏覽器一定會帶 Origin；沒有 Origin 的是非瀏覽器 client（smoke test、CLI 工具），放行。
    """
    origin = websocket.headers.get("origin")
    if origin is None:
        return True
    origin = origin.lower()
    if urlsplit(origin).netloc == websocket.headers.get("host", "").lower():
        return True
    extra = get_settings().allowed_origins.lower().split(",")
    return origin in {o.strip() for o in extra if o.strip()}


@app.websocket("/ws/gps")
async def ws_gps(websocket: WebSocket) -> None:
    """先送 snapshot（歷史軌跡），之後每筆 fix 即時推送。"""
    if not origin_allowed(websocket):
        # accept 之前 close，client 收到的是 HTTP 403
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return
    await websocket.accept()
    hub: TelemetryHub = websocket.app.state.hub
    with hub.subscribe() as (snapshot, queue):
        # 送與收各一個 task，任一邊結束就取消整組；伺服器關閉時的取消也會傳到兩邊
        async with anyio.create_task_group() as tg:

            async def send_fixes() -> None:
                try:
                    snapshot_message = SnapshotMessage(session=hub.session, points=snapshot)
                    await websocket.send_text(snapshot_message.model_dump_json())
                    while True:
                        fix = await queue.get()
                        await websocket.send_text(FixMessage(data=fix).model_dump_json())
                except (WebSocketDisconnect, OSError):
                    pass  # 送到一半 client 斷線
                tg.cancel_scope.cancel()

            async def wait_for_disconnect() -> None:
                # 目前 client 不送資料；持續 receive 是為了在斷線當下就知道，
                # 不必等到下一次 send 失敗（publisher 停了的時候可能一直等不到）
                while (await websocket.receive())["type"] != "websocket.disconnect":
                    pass
                tg.cancel_scope.cancel()

            tg.start_soon(send_fixes)
            tg.start_soon(wait_for_disconnect)

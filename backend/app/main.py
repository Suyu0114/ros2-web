import asyncio
from contextlib import asynccontextmanager
from typing import Annotated

import anyio
from fastapi import FastAPI, Query, Request, WebSocket, WebSocketDisconnect

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


@app.websocket("/ws/gps")
async def ws_gps(websocket: WebSocket) -> None:
    """先送 snapshot（歷史軌跡），之後每筆 fix 即時推送。"""
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

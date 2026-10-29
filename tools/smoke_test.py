#!/usr/bin/env python3
"""端到端冒煙測試：經由 nginx 的同源入口連 WebSocket，確認整條鏈路
（ROS 2 publisher → DDS → FastAPI bridge → nginx → client）都在運作。

    python tools/smoke_test.py [--base http://localhost:8080] [--seconds 3]

檢查項目：
1. /api/healthz 回應，且在 --wait 秒內開始收到 fix
2. WebSocket 第一則是非空的 snapshot
3. 之後的 fix 頻率約 5Hz、seq 遞增、座標在蘇澳港附近
4. 跨站 Origin 的 WebSocket 會被拒絕（403）；同源的可以連（第 2、3 項就是帶同源 Origin 連的）

需要 websockets 套件（backend 的依賴已包含；或 pip install websockets）。
"""

from __future__ import annotations

import argparse
import asyncio
import itertools
import json
import sys
import time
import urllib.request

import websockets
from websockets.exceptions import InvalidStatus

LAT_RANGE = (24.55, 24.62)  # 蘇澳港與東南外海
LON_RANGE = (121.85, 121.94)


def wait_until_fixes_flow(base: str, timeout_s: float) -> dict:
    deadline = time.monotonic() + timeout_s
    last_error = "no response"
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(f"{base}/api/healthz", timeout=3) as response:
                health = json.load(response)
            age = health.get("last_fix_age_s")
            if age is not None and age < 2:
                return health
            last_error = f"no recent fix yet: {health}"
        except OSError as exc:
            last_error = str(exc)
        time.sleep(1)
    raise SystemExit(f"FAIL healthz: {last_error}")


async def collect(ws_url: str, origin: str, seconds: float) -> tuple[list[dict], list[dict]]:
    # 帶上與頁面相同的 Origin，模擬瀏覽器（也驗證 nginx 轉給 backend 的 Host 含 port）
    async with websockets.connect(ws_url, origin=origin, open_timeout=5) as ws:
        first = json.loads(await asyncio.wait_for(ws.recv(), timeout=5))
        if first.get("type") != "snapshot":
            raise SystemExit(f"FAIL first message is not a snapshot: {first.get('type')}")
        fixes: list[dict] = []
        deadline = time.monotonic() + seconds
        while (remaining := deadline - time.monotonic()) > 0:
            try:
                message = json.loads(await asyncio.wait_for(ws.recv(), timeout=remaining))
            except TimeoutError:
                break
            if message.get("type") != "fix":
                raise SystemExit(f"FAIL unexpected message type: {message.get('type')}")
            fixes.append(message["data"])
        return first["points"], fixes


async def cross_site_status(ws_url: str) -> int | None:
    """以別的網站的 Origin 連線；回傳被拒絕時的 HTTP 狀態碼，連上了就回傳 None。"""
    try:
        async with websockets.connect(ws_url, origin="https://evil.example", open_timeout=5):
            return None
    except InvalidStatus as exc:
        return exc.response.status_code


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--base", default="http://localhost:8080")
    parser.add_argument("--seconds", type=float, default=3.0, help="收集 fix 的時間")
    parser.add_argument("--wait", type=float, default=60.0, help="等待資料開始流動的上限（秒）")
    args = parser.parse_args()
    base = args.base.rstrip("/")
    ws_url = base.replace("http", "ws", 1) + "/ws/gps"

    health = wait_until_fixes_flow(base, args.wait)
    print(f"ok   healthz: {health}")

    snapshot, fixes = asyncio.run(collect(ws_url, base, args.seconds))
    rate = len(fixes) / args.seconds
    failures = []
    cross_site = asyncio.run(cross_site_status(ws_url))
    if cross_site != 403:
        failures.append(f"cross-site WebSocket was not rejected with 403 (got {cross_site})")
    if not snapshot:
        failures.append("snapshot is empty")
    if not 4.0 <= rate <= 6.0:
        failures.append(f"rate {rate:.2f} Hz is not about 5 Hz")
    seqs = [f["seq"] for f in snapshot + fixes]
    if any(b <= a for a, b in itertools.pairwise(seqs)):
        failures.append("seq is not strictly increasing across snapshot and live fixes")
    outside = [
        f
        for f in fixes
        if not (LAT_RANGE[0] < f["lat"] < LAT_RANGE[1] and LON_RANGE[0] < f["lon"] < LON_RANGE[1])
    ]
    if outside:
        failures.append(f"{len(outside)} fixes outside the Su'ao harbor area, e.g. {outside[0]}")

    print(f"ok   snapshot: {len(snapshot)} points")
    verdict = "ok  " if 4.0 <= rate <= 6.0 else "FAIL"
    print(f"{verdict} live: {len(fixes)} fixes in {args.seconds:.0f}s = {rate:.2f} Hz")
    if cross_site == 403:
        print("ok   cross-site origin rejected: 403")
    for failure in failures:
        print(f"FAIL {failure}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())

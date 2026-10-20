"""開發用：不需要 ROS，把路徑 CSV 依固定頻率灌進 backend 的 TelemetryHub。

跑的是真正的 backend（同一份 hub、WebSocket、REST），只有資料來源從 ROS 換成 CSV，
方便在沒有 Docker / ROS 的機器上開發前端：

    cd backend
    python dev/replay_csv.py ../data/path_data.csv --start 900
    cd ../frontend && npm run dev   # Vite 會把 /api、/ws 轉到 :8000

不會被打包進 image（Dockerfile 只複製 app/）。
"""

import argparse
import asyncio
import csv
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ["BRIDGE_ROS_ENABLED"] = "false"

import uvicorn  # noqa: E402

from app.main import app  # noqa: E402
from app.schemas import GpsFix  # noqa: E402


def load_points(path: Path) -> list[tuple[float, float]]:
    with path.open(encoding="utf-8") as f:
        return [(float(row["latitude"]), float(row["longitude"])) for row in csv.DictReader(f)]


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("csv", type=Path)
    parser.add_argument("--rate", type=float, default=5.0, help="每秒幾筆（預設 5）")
    parser.add_argument("--start", type=int, default=0, help="從第幾點開始播")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

    points = load_points(args.csv)
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=args.port))

    async def feed() -> None:
        while not server.started:  # noqa: ASYNC110 — uvicorn 只提供旗標，沒有可等待的 event
            await asyncio.sleep(0.05)
        hub = app.state.hub
        seq, index = 0, args.start % len(points)
        while not server.should_exit:
            lat, lon = points[index]
            seq += 1
            t = time.time_ns() // 1_000_000
            hub.publish(GpsFix(seq=seq, t=t, lat=lat, lon=lon, alt=0.0, status=0, frame_id="gps"))
            index = (index + 1) % len(points)
            await asyncio.sleep(1 / args.rate)

    await asyncio.gather(server.serve(), feed())


if __name__ == "__main__":
    asyncio.run(main())

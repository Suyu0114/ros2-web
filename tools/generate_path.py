#!/usr/bin/env python3
"""產生 data/path_data.csv：高雄港內 → 第一港口 → 外海巡邏 → 回港的封閉航線。

航點為手選，並在 OSM 圖磚上確認都在水面上。相鄰航點之間沿大圓每
--spacing 公尺內插一點。Publisher 以 5Hz 播放，預設 2 m 間距約等於
10 m/s（約 19 節）。

只用標準函式庫：
    python tools/generate_path.py [--spacing 2.0] [--out data/path_data.csv]
"""

from __future__ import annotations

import argparse
import csv
import itertools
import math
from pathlib import Path

EARTH_RADIUS_M = 6_371_008.8

# (latitude, longitude)。最後一點會自動接回第一點，形成封閉迴圈。
# 航道靠右行駛：出港（向西）走北側，進港（向東）走南側。
# 哨船頭與旗後之間的窄水道寬約 100 m（約 22.6162–22.6171），兩條航道各離岸約 30 m。
WAYPOINTS: list[tuple[float, float]] = [
    (22.6166, 120.2790),  # 港內，蓬萊碼頭外水域（起點）
    (22.6170, 120.2745),  # 出港航道，台樂碼頭外
    (22.6170, 120.2690),
    (22.6168, 120.2650),  # 窄水道（哨船頭—旗後）北側
    (22.6180, 120.2605),
    (22.6199, 120.2566),  # 第一港口，綠燈塔與紅燈塔之間偏北
    (22.6215, 120.2480),  # 出港
    (22.6260, 120.2400),  # 巡邏區：北
    (22.6120, 120.2370),  # 巡邏區：西
    (22.6080, 120.2470),  # 巡邏區：南
    (22.6165, 120.2500),  # 回航，從紅燈塔以西繞進港口
    (22.6189, 120.2560),  # 第一港口偏南
    (22.6172, 120.2600),
    (22.6165, 120.2650),  # 窄水道南側
    (22.6160, 120.2690),  # 進港航道
    (22.6158, 120.2745),
    (22.6152, 120.2785),
    (22.6156, 120.2805),  # 迴船，接回起點
]


def _to_vec(lat: float, lon: float) -> tuple[float, float, float]:
    phi, lam = math.radians(lat), math.radians(lon)
    return (math.cos(phi) * math.cos(lam), math.cos(phi) * math.sin(lam), math.sin(phi))


def _to_latlon(v: tuple[float, float, float]) -> tuple[float, float]:
    x, y, z = v
    return math.degrees(math.atan2(z, math.hypot(x, y))), math.degrees(math.atan2(y, x))


def haversine_m(a: tuple[float, float], b: tuple[float, float]) -> float:
    phi1, phi2 = math.radians(a[0]), math.radians(b[0])
    dphi, dlam = phi2 - phi1, math.radians(b[1] - a[1])
    h = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    return 2 * EARTH_RADIUS_M * math.asin(math.sqrt(h))


def _slerp(a: tuple[float, float], b: tuple[float, float], t: float) -> tuple[float, float]:
    va, vb = _to_vec(*a), _to_vec(*b)
    omega = math.acos(max(-1.0, min(1.0, sum(p * q for p, q in zip(va, vb, strict=True)))))
    if omega < 1e-12:
        return a
    sa, sb = math.sin((1 - t) * omega) / math.sin(omega), math.sin(t * omega) / math.sin(omega)
    return _to_latlon(tuple(sa * p + sb * q for p, q in zip(va, vb, strict=True)))  # type: ignore[arg-type]


def densify(waypoints: list[tuple[float, float]], spacing_m: float) -> list[tuple[float, float]]:
    """沿封閉迴圈每 spacing_m 公尺取一點（不重複最後回到起點的那一點）。"""
    points: list[tuple[float, float]] = []
    loop = waypoints + waypoints[:1]
    for a, b in itertools.pairwise(loop):
        steps = max(1, round(haversine_m(a, b) / spacing_m))
        points.extend(_slerp(a, b, i / steps) for i in range(steps))
    return points


def main() -> None:
    root = Path(__file__).resolve().parent.parent
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--spacing", type=float, default=2.0, help="內插間距（公尺）")
    parser.add_argument("--out", type=Path, default=root / "data" / "path_data.csv")
    args = parser.parse_args()

    points = densify(WAYPOINTS, args.spacing)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, lineterminator="\n")
        writer.writerow(["latitude", "longitude", "altitude"])
        writer.writerows((f"{lat:.7f}", f"{lon:.7f}", "0.0") for lat, lon in points)

    length = sum(haversine_m(a, b) for a, b in zip(points, points[1:] + points[:1], strict=True))
    print(f"{len(points)} points, loop {length / 1000:.2f} km -> {args.out}")


if __name__ == "__main__":
    main()

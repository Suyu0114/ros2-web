#!/usr/bin/env python3
"""產生 data/path_data.csv：蘇澳港中央港池 → 港口 → 東南外海巡邏 → 回港的封閉航線。

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
# - 只用商港水域與外海：北側內港（約 24.597 以北）是軍港區，全程避開。
# - 港口開口在北防波堤南端與東防波堤北端之間，寬約 220 m，朝東北東。
#   依靠右航行的慣例，出港走開口南半，進港走北半；港外逆時針巡邏，進出路線不交叉。
WAYPOINTS: list[tuple[float, float]] = [
    (24.5915, 121.8725),  # 中央港池（起點）
    (24.5925, 121.8770),  # 出港航道
    (24.5939, 121.8813),  # 港口開口南半
    (24.5935, 121.8860),  # 出港，轉向東南
    (24.5880, 121.8920),  # 巡邏區：沿東防波堤外側南下
    (24.5740, 121.9040),  # 巡邏區：南
    (24.5800, 121.9200),  # 巡邏區：東
    (24.5945, 121.9120),  # 巡邏區：北（與北方澳外的小島保持 300 m 以上）
    (24.5950, 121.8900),  # 回航，對準港口
    (24.5952, 121.8850),
    (24.5948, 121.8818),  # 港口開口北半
    (24.5935, 121.8770),  # 進港航道
    (24.5930, 121.8715),  # 迴船，接回起點
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

from types import SimpleNamespace

from app.schemas import GpsFix


def make_fix(seq: int, lat: float = 22.6166, lon: float = 120.279) -> GpsFix:
    t = 1_760_000_000_000 + seq * 200
    return GpsFix(seq=seq, t=t, lat=lat, lon=lon, alt=0.0, status=0, frame_id="gps")


def fake_navsatfix(lat=22.6166, lon=120.279, alt=0.0, status=0, sec=1_760_000_000, nanosec=250_000_000):
    """欄位與 sensor_msgs/NavSatFix 相同的替身，沒有 rclpy 時用。"""
    return SimpleNamespace(
        header=SimpleNamespace(stamp=SimpleNamespace(sec=sec, nanosec=nanosec), frame_id="gps"),
        status=SimpleNamespace(status=status, service=1),
        latitude=lat,
        longitude=lon,
        altitude=alt,
    )

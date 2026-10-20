import asyncio
import time
import uuid
from collections import deque
from collections.abc import Iterator
from contextlib import contextmanager

from app.schemas import GpsFix


class TelemetryHub:
    """保存最近的軌跡，並把每筆新的 fix 廣播給所有 WebSocket client。

    所有方法都只能在 asyncio event loop 的執行緒呼叫。ROS 執行緒要用
    loop.call_soon_threadsafe(hub.publish, fix) 把資料交過來。
    """

    def __init__(self, history_size: int, client_queue_size: int) -> None:
        self.session = uuid.uuid4().hex[:12]  # 每次啟動不同，見 SnapshotMessage.session
        self._history: deque[GpsFix] = deque(maxlen=history_size)
        self._clients: set[asyncio.Queue[GpsFix]] = set()
        self._client_queue_size = client_queue_size
        self.fixes_received = 0
        self.dropped = 0  # 因 client 太慢而丟掉的訊息數
        self._last_fix_at: float | None = None

    def publish(self, fix: GpsFix) -> None:
        self._history.append(fix)
        self.fixes_received += 1
        self._last_fix_at = time.monotonic()
        for queue in self._clients:
            if queue.full():
                # 慢的 client 丟掉最舊的一筆，不會拖慢其他 client，也不會無限累積記憶體
                queue.get_nowait()
                self.dropped += 1
            queue.put_nowait(fix)

    def history(self, limit: int | None = None) -> list[GpsFix]:
        points = list(self._history)
        return points[-limit:] if limit else points

    @contextmanager
    def subscribe(self) -> Iterator[tuple[list[GpsFix], "asyncio.Queue[GpsFix]"]]:
        """註冊一個 client，回傳（當下的歷史快照，之後的即時佇列）。

        快照和註冊在同一個同步區塊內完成，兩者之間不會漏掉或重複任何一筆。
        """
        queue: asyncio.Queue[GpsFix] = asyncio.Queue(maxsize=self._client_queue_size)
        self._clients.add(queue)
        try:
            yield list(self._history), queue
        finally:
            self._clients.discard(queue)

    @property
    def client_count(self) -> int:
        return len(self._clients)

    @property
    def last_fix_age_s(self) -> float | None:
        if self._last_fix_at is None:
            return None
        return time.monotonic() - self._last_fix_at

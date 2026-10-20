# syntax=docker/dockerfile:1
#   docker build backend                # runtime image
#   docker build --target test backend  # ruff + pytest（含真的 rclpy 測試），失敗即建置失敗

FROM ros:jazzy-ros-core AS base
RUN apt-get update \
 && apt-get install -y --no-install-recommends python3-venv \
 && rm -rf /var/lib/apt/lists/*
# --system-site-packages：venv 內仍看得到 apt 裝的 ROS Python 套件（rclpy、sensor_msgs）
ENV VIRTUAL_ENV=/opt/venv \
    PATH=/opt/venv/bin:$PATH \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
RUN python3 -m venv --system-site-packages "$VIRTUAL_ENV"
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --require-hashes -r requirements.txt
COPY app ./app

FROM base AS test
COPY requirements-dev.txt pyproject.toml ./
RUN pip install --no-cache-dir --require-hashes -r requirements-dev.txt
COPY tests ./tests
RUN ruff check . && ruff format --check . \
 && . "/opt/ros/$ROS_DISTRO/setup.sh" && pytest -q

FROM base AS runtime
RUN useradd --create-home --uid 10001 bridge
USER bridge
EXPOSE 8000
HEALTHCHECK --interval=10s --timeout=3s --start-period=10s --retries=3 \
  CMD ["python3", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/healthz', timeout=2)"]
# 基底 image 的 /ros_entrypoint.sh 會先 source ROS 環境
ENTRYPOINT ["/ros_entrypoint.sh"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

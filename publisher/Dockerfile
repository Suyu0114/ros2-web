# syntax=docker/dockerfile:1
# Build context：repo 根目錄（才拿得到 data/path_data.csv）
#   docker build -f publisher/Dockerfile .                # runtime image
#   docker build -f publisher/Dockerfile --target test .  # 跑 gtest，失敗即建置失敗

FROM ros:jazzy-ros-base AS build
WORKDIR /ws
COPY publisher/gnss_publisher src/gnss_publisher
RUN apt-get update \
 && rosdep install --from-paths src --ignore-src -y --rosdistro "$ROS_DISTRO" \
 && rm -rf /var/lib/apt/lists/*
RUN . "/opt/ros/$ROS_DISTRO/setup.sh" \
 && colcon build --merge-install --event-handlers console_direct+ \
      --cmake-args -DCMAKE_BUILD_TYPE=Release

FROM build AS test
RUN . "/opt/ros/$ROS_DISTRO/setup.sh" \
 && colcon test --merge-install --event-handlers console_direct+ \
 && colcon test-result --verbose

FROM ros:jazzy-ros-core AS runtime
COPY --from=build /ws/install /ws/install
COPY data/path_data.csv /data/path_data.csv
COPY --chmod=755 publisher/entrypoint.sh /entrypoint.sh
ENTRYPOINT ["/entrypoint.sh"]
CMD ["ros2", "launch", "gnss_publisher", "gnss_publisher.launch.py"]

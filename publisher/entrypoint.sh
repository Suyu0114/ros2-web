#!/bin/bash
# 載入 ROS 與本 workspace 的環境後執行指令。
# 進容器除錯也走這裡：docker compose exec publisher /entrypoint.sh ros2 topic hz /gps/fix
set -e
source "/opt/ros/${ROS_DISTRO}/setup.bash"
source /ws/install/setup.bash
exec "$@"

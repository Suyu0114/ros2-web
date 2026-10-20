cmake_minimum_required(VERSION 3.8)
project(gnss_publisher)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_package(sensor_msgs REQUIRED)

# CSV 解析不依賴 ROS，獨立成靜態函式庫，節點與單元測試共用
add_library(csv_path_loader STATIC src/csv_path_loader.cpp)
target_include_directories(csv_path_loader PUBLIC
  $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>)

add_executable(gnss_publisher_node src/gnss_publisher_node.cpp)
target_link_libraries(gnss_publisher_node
  csv_path_loader
  rclcpp::rclcpp
  ${sensor_msgs_TARGETS})

install(TARGETS gnss_publisher_node DESTINATION lib/${PROJECT_NAME})
install(DIRECTORY launch config DESTINATION share/${PROJECT_NAME})

if(BUILD_TESTING)
  find_package(ament_cmake_gtest REQUIRED)
  ament_add_gtest(test_csv_path_loader test/test_csv_path_loader.cpp)
  target_link_libraries(test_csv_path_loader csv_path_loader)
endif()

ament_package()

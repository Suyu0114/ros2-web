#include <chrono>
#include <memory>
#include <string>
#include <utility>
#include <vector>

#include "gnss_publisher/csv_path_loader.hpp"
#include "rclcpp/rclcpp.hpp"
#include "sensor_msgs/msg/nav_sat_fix.hpp"

namespace gnss_publisher
{

/// 讀取 GPS 路徑 CSV，以固定頻率把每一點發佈成 NavSatFix；到最後一點時從頭循環。
class GnssPublisherNode : public rclcpp::Node
{
public:
  explicit GnssPublisherNode(const rclcpp::NodeOptions & options = rclcpp::NodeOptions())
  : Node("gnss_publisher", options)
  {
    const auto csv_path = declare_parameter<std::string>("csv_path", "/data/path_data.csv");

    rcl_interfaces::msg::ParameterDescriptor rate_descriptor;
    rate_descriptor.description = "Publish rate in Hz";
    rate_descriptor.read_only = true;
    rate_descriptor.floating_point_range.resize(1);
    rate_descriptor.floating_point_range[0].from_value = 0.1;
    rate_descriptor.floating_point_range[0].to_value = 100.0;
    const auto rate_hz = declare_parameter<double>("publish_rate_hz", 5.0, rate_descriptor);

    frame_id_ = declare_parameter<std::string>("frame_id", "gps");
    loop_ = declare_parameter<bool>("loop", true);

    auto loaded = load_path_csv(csv_path);
    for (const auto & warning : loaded.warnings) {
      RCLCPP_WARN(get_logger(), "%s: skipped %s", csv_path.c_str(), warning.c_str());
    }
    points_ = std::move(loaded.points);

    // 感測器資料：best effort、只保留最新幾筆；訂閱端需用相容的 QoS（sensor data profile）
    publisher_ = create_publisher<sensor_msgs::msg::NavSatFix>("gps/fix", rclcpp::SensorDataQoS());
    const auto period = std::chrono::duration_cast<std::chrono::nanoseconds>(
      std::chrono::duration<double>(1.0 / rate_hz));
    timer_ = create_wall_timer(period, [this]() {on_timer();});

    RCLCPP_INFO(
      get_logger(), "Loaded %zu points from %s; publishing %s at %.1f Hz (loop=%s)",
      points_.size(), csv_path.c_str(), publisher_->get_topic_name(), rate_hz,
      loop_ ? "true" : "false");
  }

private:
  void on_timer()
  {
    if (index_ == points_.size()) {
      if (!loop_) {
        RCLCPP_INFO(get_logger(), "Reached the end of the path; stopping");
        timer_->cancel();
        return;
      }
      index_ = 0;
      ++laps_;
      RCLCPP_INFO(get_logger(), "Completed lap %zu; restarting from the first point", laps_);
    }
    const auto & point = points_[index_++];

    sensor_msgs::msg::NavSatFix msg;
    msg.header.stamp = now();
    msg.header.frame_id = frame_id_;
    msg.status.status = sensor_msgs::msg::NavSatStatus::STATUS_FIX;
    msg.status.service = sensor_msgs::msg::NavSatStatus::SERVICE_GPS;
    msg.latitude = point.latitude;
    msg.longitude = point.longitude;
    msg.altitude = point.altitude;
    msg.position_covariance_type = sensor_msgs::msg::NavSatFix::COVARIANCE_TYPE_UNKNOWN;
    publisher_->publish(msg);
  }

  rclcpp::Publisher<sensor_msgs::msg::NavSatFix>::SharedPtr publisher_;
  rclcpp::TimerBase::SharedPtr timer_;
  std::vector<GeoPoint> points_;
  std::size_t index_{0};
  std::size_t laps_{0};
  std::string frame_id_;
  bool loop_{true};
};

}  // namespace gnss_publisher

int main(int argc, char ** argv)
{
  rclcpp::init(argc, argv);
  int exit_code = 0;
  try {
    rclcpp::spin(std::make_shared<gnss_publisher::GnssPublisherNode>());
  } catch (const std::exception & e) {
    RCLCPP_FATAL(rclcpp::get_logger("gnss_publisher"), "%s", e.what());
    exit_code = 1;
  }
  rclcpp::shutdown();
  return exit_code;
}

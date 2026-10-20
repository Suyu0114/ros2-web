from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    default_params = PathJoinSubstitution(
        [FindPackageShare('gnss_publisher'), 'config', 'params.yaml'])
    return LaunchDescription([
        DeclareLaunchArgument(
            'params_file', default_value=default_params,
            description='Parameter file for gnss_publisher (csv_path, publish_rate_hz, ...)'),
        Node(
            package='gnss_publisher',
            executable='gnss_publisher_node',
            name='gnss_publisher',
            parameters=[LaunchConfiguration('params_file')],
            output='screen',
            emulate_tty=True,
        ),
    ])

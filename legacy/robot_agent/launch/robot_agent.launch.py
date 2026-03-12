from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description() -> LaunchDescription:
    return LaunchDescription(
        [
            DeclareLaunchArgument("mqtt_host", default_value="127.0.0.1"),
            DeclareLaunchArgument("mqtt_port", default_value="1883"),
            DeclareLaunchArgument("topic_prefix", default_value="hrd"),
            DeclareLaunchArgument("robot_id", default_value="robot-001"),
            DeclareLaunchArgument("camera_topic", default_value="/camera/color/image_raw"),
            DeclareLaunchArgument("jpeg_quality", default_value="90"),
            Node(
                package="robot_agent",
                executable="capture_agent",
                name="capture_agent",
                output="screen",
                parameters=[
                    {
                        "mqtt_host": LaunchConfiguration("mqtt_host"),
                        "mqtt_port": LaunchConfiguration("mqtt_port"),
                        "topic_prefix": LaunchConfiguration("topic_prefix"),
                        "robot_id": LaunchConfiguration("robot_id"),
                        "camera_topic": LaunchConfiguration("camera_topic"),
                        "jpeg_quality": LaunchConfiguration("jpeg_quality"),
                    }
                ],
            ),
        ]
    )

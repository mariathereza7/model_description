import os
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition, UnlessCondition
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory


def generate_launch_description():
    share = get_package_share_directory('meu_robo_control')
    params = os.path.join(share, 'config', 'slam_toolbox.yaml')
    odom_params = os.path.join(share, 'config', 'odom_noise.yaml')
    noisy = LaunchConfiguration('odom_noise')
    return LaunchDescription([
        DeclareLaunchArgument('odom_noise', default_value='false'),
        Node(package='meu_robo_control', executable='odom_noise_node',
             parameters=[odom_params], output='screen', condition=IfCondition(noisy)),
        Node(package='slam_toolbox', executable='async_slam_toolbox_node',
             parameters=[params], output='screen',
             remappings=[('/odom', '/odom_noisy')], condition=IfCondition(noisy)),
        Node(package='slam_toolbox', executable='async_slam_toolbox_node',
             name='slam_toolbox', parameters=[params], output='screen',
             remappings=[('/odom', '/diff_drive_base_controller/odom')],
             condition=UnlessCondition(noisy)),
    ])

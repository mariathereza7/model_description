"""Run the figure-eight trajectory using robot_localization EKF output."""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition, UnlessCondition
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    share = get_package_share_directory('meu_robo_control')
    ekf_config = os.path.join(share, 'config', 'ekf.yaml')
    use_fusion = LaunchConfiguration('use_sensor_fusion')
    return LaunchDescription([
        DeclareLaunchArgument(
            'use_sensor_fusion', default_value='true',
            description='Usa sensores via EKF quando true; usa odometria direta quando false.'),
        Node(
            package='robot_localization',
            executable='ekf_node',
            name='ekf_filter_node',
            parameters=[ekf_config, {'use_sim_time': True}],
            condition=IfCondition(use_fusion),
            output='screen',
        ),
        Node(
            package='meu_robo_control',
            executable='trajectory_node',
            parameters=[
                os.path.join(share, 'config', 'trajectory_params.yaml'),
                {'use_sim_time': True},
            ],
            remappings=[
                ('/odom', '/odometry/filtered'),
                ('/cmd_vel', '/diff_drive_base_controller/cmd_vel_unstamped'),
            ],
            condition=IfCondition(use_fusion),
            output='screen',
        ),
        Node(
            package='meu_robo_control',
            executable='trajectory_node',
            parameters=[
                os.path.join(share, 'config', 'trajectory_params.yaml'),
                {'use_sim_time': True},
            ],
            remappings=[
                ('/odom', '/diff_drive_base_controller/odom'),
                ('/cmd_vel', '/diff_drive_base_controller/cmd_vel_unstamped'),
            ],
            condition=UnlessCondition(use_fusion),
            output='screen',
        ),
    ])

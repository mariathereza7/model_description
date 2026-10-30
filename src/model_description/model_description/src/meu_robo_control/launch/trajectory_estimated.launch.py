"""Run the figure-eight trajectory using robot_localization EKF output."""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    share = get_package_share_directory('meu_robo_control')
    ekf_config = os.path.join(share, 'config', 'ekf.yaml')
    return LaunchDescription([
        Node(
            package='robot_localization',
            executable='ekf_node',
            name='ekf_filter_node',
            parameters=[ekf_config, {'use_sim_time': True}],
            output='screen',
        ),
        Node(
            package='meu_robo_control',
            executable='trajectory_node',
            parameters=[
                {'use_sim_time': True},
                {'max_linear_speed': 0.6},
                {'max_angular_speed': 1.5},
            ],
            remappings=[
                ('/odom', '/odometry/filtered'),
                ('/cmd_vel', '/diff_drive_base_controller/cmd_vel_unstamped'),
            ],
            output='screen',
        ),
    ])

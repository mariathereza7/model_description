"""Run the trajectory controller against the running Gazebo simulation."""

import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    params = os.path.join(get_package_share_directory('meu_robo_control'), 'config', 'trajectory_params.yaml')
    return LaunchDescription([
        Node(
            package='meu_robo_control',
            executable='trajectory_node',
            output='screen',
            parameters=[params, {'use_sim_time': True}],
            remappings=[
                ('/odom', '/diff_drive_base_controller/odom'),
                ('/cmd_vel', '/diff_drive_base_controller/cmd_vel_unstamped'),
            ],
        ),
    ])

"""Run the waypoint mission with rotate-translate-rotate control."""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    share = get_package_share_directory('meu_robo_control')
    waypoints = os.path.join(share, 'config', 'waypoints.yaml')
    params = os.path.join(share, 'config', 'maneuver_params.yaml')
    return LaunchDescription([
        Node(package='meu_robo_control', executable='maneuver_pose_node',
             parameters=[params, {'use_sim_time': True}],
             remappings=[('/odom', '/diff_drive_base_controller/odom'),
                         ('/cmd_vel', '/diff_drive_base_controller/cmd_vel_unstamped')],
             output='screen'),
        Node(package='meu_robo_control', executable='mission_node',
             parameters=[waypoints, {'use_sim_time': True}],
             remappings=[('/odom', '/diff_drive_base_controller/odom')],
             output='screen'),
    ])

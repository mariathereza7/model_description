"""Run the mission and pose controller against the existing simulation."""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    config = os.path.join(get_package_share_directory('meu_robo_control'),
                          'config', 'waypoints.yaml')
    controller_config = os.path.join(
        get_package_share_directory('meu_robo_control'),
        'config', 'controller_params.yaml')
    odom = ('/odom', '/diff_drive_base_controller/odom')
    return LaunchDescription([
        Node(package='meu_robo_control', executable='pose_control_node',
             parameters=[controller_config, {'use_sim_time': True},
                         {'max_linear_speed': 0.6},
                         {'max_angular_speed': 1.5}],
             remappings=[odom, ('/cmd_vel', '/diff_drive_base_controller/cmd_vel_unstamped')],
             output='screen'),
        Node(package='meu_robo_control', executable='mission_node',
             parameters=[config, {'use_sim_time': True}],
             remappings=[odom], output='screen'),
    ])

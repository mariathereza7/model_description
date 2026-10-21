"""Run the GPS geographic-to-local coordinate converter."""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    config = os.path.join(get_package_share_directory('meu_robo_control'),
                          'config', 'gps_params.yaml')
    return LaunchDescription([
        Node(
            package='meu_robo_control',
            executable='gps_to_local_node',
            parameters=[config, {'use_sim_time': True}],
            output='screen',
        ),
    ])

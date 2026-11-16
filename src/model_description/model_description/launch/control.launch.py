import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    share = get_package_share_directory('meu_robo_control')
    config = os.path.join(share, 'config')
    return LaunchDescription([
        Node(package='meu_robo_control', executable='mission_node', name='mission_node',
             parameters=[os.path.join(config, 'waypoints.yaml')]),
        Node(package='meu_robo_control', executable='pose_control_node', name='pose_controller',
             parameters=[os.path.join(config, 'controller_params.yaml')]),
    ])

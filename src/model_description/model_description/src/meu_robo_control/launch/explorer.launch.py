import os
from launch import LaunchDescription
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory


def generate_launch_description():
    params = os.path.join(
        get_package_share_directory('meu_robo_control'), 'config', 'explorer_params.yaml')
    return LaunchDescription([
        Node(package='meu_robo_control', executable='explorer_node',
             name='explorer_node', parameters=[params], output='screen')
    ])

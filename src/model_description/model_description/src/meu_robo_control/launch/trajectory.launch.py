"""Run the trajectory controller against the running Gazebo simulation."""

from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    return LaunchDescription([
        Node(
            package='meu_robo_control',
            executable='trajectory_node',
            output='screen',
            parameters=[{'use_sim_time': True},
                        {'max_linear_speed': 0.6},
                        {'max_angular_speed': 1.5}],
            remappings=[
                ('/odom', '/diff_drive_base_controller/odom'),
                ('/cmd_vel', '/diff_drive_base_controller/cmd_vel_unstamped'),
            ],
        ),
    ])

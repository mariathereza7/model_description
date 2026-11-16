import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription, DeclareLaunchArgument
from launch.conditions import IfCondition, UnlessCondition
from launch.substitutions import LaunchConfiguration
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node

def generate_launch_description():
    package_name = 'meu_robo_control'
    
    urdf_file_path = os.path.join(
        get_package_share_directory(package_name), 'urdf', 'robot.urdf'
    )
    urdf_no_noise_path = os.path.join(
        get_package_share_directory(package_name), 'urdf', 'robot_no_noise.urdf'
    )

    with open(urdf_file_path, 'r') as infp:
        robot_desc = infp.read()
    # Resolve the package path before passing the plain URDF to Gazebo.
    robot_desc = robot_desc.replace(
        "$(find meu_robo_control)", get_package_share_directory(package_name)
    )
    with open(urdf_no_noise_path, 'r') as infp:
        robot_desc_no_noise = infp.read().replace(
            "$(find meu_robo_control)", get_package_share_directory(package_name))
    sensor_noise = LaunchConfiguration('sensor_noise')

    gazebo = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([
            os.path.join(get_package_share_directory('gazebo_ros'), 'launch', 'gazebo.launch.py')
        ]),
        launch_arguments={'server_required': 'true'}.items(),
    )

    spawn_entity = Node(
        package='gazebo_ros',
        executable='spawn_entity.py',
        arguments=['-entity', 'meu_robo', '-topic', 'robot_description'],
        output='screen', condition=IfCondition(sensor_noise)
    )
    spawn_entity_no_noise = Node(
        package='gazebo_ros', executable='spawn_entity.py',
        arguments=['-entity', 'meu_robo', '-topic', 'robot_description'],
        output='screen', condition=UnlessCondition(sensor_noise)
    )

    robot_state_publisher = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        output='screen',
        parameters=[{'robot_description': robot_desc}],
        condition=IfCondition(sensor_noise)
    )
    robot_state_publisher_no_noise = Node(
        package='robot_state_publisher', executable='robot_state_publisher',
        output='screen', parameters=[{'robot_description': robot_desc_no_noise}],
        condition=UnlessCondition(sensor_noise)
    )

    return LaunchDescription([
        DeclareLaunchArgument('sensor_noise', default_value='true',
                              description='Ativa o ruído dos sensores do URDF'),
        gazebo,
        robot_state_publisher,
        robot_state_publisher_no_noise,
        spawn_entity,
        spawn_entity_no_noise,
    ])

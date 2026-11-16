import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription, DeclareLaunchArgument, RegisterEventHandler
from launch.event_handlers import OnProcessExit
from launch.conditions import IfCondition, UnlessCondition
from launch.substitutions import LaunchConfiguration
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node

def generate_launch_description():
    package_name = 'meu_robo_control'
    pkg_share = get_package_share_directory(package_name)

    urdf_file = os.path.join(pkg_share, 'urdf', 'robot.urdf')
    urdf_no_noise_file = os.path.join(pkg_share, 'urdf', 'robot_no_noise.urdf')
    with open(urdf_file, 'r') as infp:
        robot_description_config = infp.read()
    # Resolve the package path before passing the plain URDF to Gazebo.
    robot_description_config = robot_description_config.replace(
        "$(find meu_robo_control)", get_package_share_directory(package_name)
    )
    with open(urdf_no_noise_file, 'r') as infp:
        robot_description_no_noise = infp.read().replace(
            "$(find meu_robo_control)", get_package_share_directory(package_name))
    sensor_noise = LaunchConfiguration('sensor_noise')
    world = LaunchConfiguration('world')
    gui = LaunchConfiguration('gui')

    # 1. Inicia o Gazebo Classic
    gazebo = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([
            os.path.join(get_package_share_directory('gazebo_ros'), 'launch', 'gazebo.launch.py')
        ]),
        launch_arguments={'server_required': 'true', 'world': world, 'gui': gui}.items(),
    )

    # 2. Publica o robot_description
    robot_state_publisher = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        output='screen',
        parameters=[{'robot_description': robot_description_config}],
        condition=IfCondition(sensor_noise),
    )
    robot_state_publisher_no_noise = Node(
        package='robot_state_publisher', executable='robot_state_publisher',
        output='screen', parameters=[{'robot_description': robot_description_no_noise}],
        condition=UnlessCondition(sensor_noise),
    )

    # 3. Carrega o robô no Gazebo
    spawn_entity = Node(
        package='gazebo_ros',
        executable='spawn_entity.py',
        arguments=['-topic', 'robot_description', '-entity', 'meu_robo'],
        output='screen', condition=IfCondition(sensor_noise)
    )
    spawn_entity_no_noise = Node(
        package='gazebo_ros', executable='spawn_entity.py',
        arguments=['-topic', 'robot_description', '-entity', 'meu_robo'],
        output='screen', condition=UnlessCondition(sensor_noise)
    )

    # 4. Spawner do Joint State Broadcaster
    joint_state_broadcaster_spawner = Node(
        package="controller_manager",
        executable="spawner",
        arguments=["joint_state_broadcaster", "--controller-manager-timeout", "60", "--service-call-timeout", "60"],
        output='screen',
    )

    # 5. Spawner do Diff Drive Controller
    diff_drive_spawner = Node(
        package="controller_manager",
        executable="spawner",
        arguments=["diff_drive_base_controller", "--controller-manager-timeout", "60", "--service-call-timeout", "60"],
        output='screen',
    )

    # O controller_manager só existe depois que o robô é inserido no Gazebo.
    # Portanto, os spawners não devem ser iniciados em paralelo com spawn_entity.
    controllers_after_spawn = RegisterEventHandler(
        OnProcessExit(
            target_action=spawn_entity,
            on_exit=[
                joint_state_broadcaster_spawner,
                diff_drive_spawner,
            ],
        )
    )
    controllers_after_spawn_no_noise = RegisterEventHandler(
        OnProcessExit(
            target_action=spawn_entity_no_noise,
            on_exit=[
                joint_state_broadcaster_spawner,
                diff_drive_spawner,
            ],
        )
    )

    # 6. Nó de controle por teclado (teleop_twist_keyboard)
    teleop_keyboard = Node(
        package='teleop_twist_keyboard',
        executable='teleop_twist_keyboard',
        name='teleop_keyboard',
        output='screen',
        prefix='xterm -e', # Abre em um novo terminal para aceitar entradas do teclado
        condition=IfCondition(LaunchConfiguration('teleop')),
        remappings=[('/cmd_vel', '/diff_drive_base_controller/cmd_vel_unstamped')]
    )

    return LaunchDescription([
        DeclareLaunchArgument('teleop', default_value='false',
                              description='Inicia o teleop em um xterm'),
        DeclareLaunchArgument('sensor_noise', default_value='true',
                              description='Ativa o ruído dos sensores do URDF'),
        DeclareLaunchArgument('world', default_value=os.path.join(
            get_package_share_directory('gazebo_ros'), 'worlds', 'empty.world'),
                              description='Mundo Gazebo opcional para SLAM'),
        DeclareLaunchArgument('gui', default_value='true',
                              description='Inicia o gzclient'),
        gazebo,
        robot_state_publisher,
        robot_state_publisher_no_noise,
        spawn_entity,
        spawn_entity_no_noise,
        controllers_after_spawn,
        controllers_after_spawn_no_noise,
        teleop_keyboard
    ])

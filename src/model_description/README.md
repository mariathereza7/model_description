# Simulação ROS 2 do robô diferencial

Este projeto contém a descrição URDF de um robô diferencial, a simulação no Gazebo Classic e nós ROS 2 para controle de pose, seguimento de missão e seguimento de trajetória em oito.

## Requisitos

- Ubuntu 22.04
- ROS 2 Humble
- Gazebo Classic 11
- `gazebo_ros2_control`
- `teleop_twist_keyboard` (opcional)
- PlotJuggler com suporte a ROS 2 (opcional)

Sempre abra cada terminal com o ambiente ROS carregado:

```bash
source /opt/ros/humble/setup.bash
source ~/ros2_ws/install/setup.bash
```

## Compilação

O projeto atual possui os pacotes dentro de `src/model_description`. Por isso, compile usando os caminhos abaixo:

```bash
source /opt/ros/humble/setup.bash
cd ~/ros2_ws

colcon build \
  --base-paths src/model_description/model_description \
  --packages-select model_description \
  --symlink-install

colcon build \
  --base-paths src/model_description/model_description/src/meu_robo_control \
  --packages-select meu_robo_control \
  --symlink-install

source install/setup.bash
```

## Inicialização do Gazebo

Em um terminal, inicie o mundo padrão e o robô `meu_robo`:

```bash
source /opt/ros/humble/setup.bash
source ~/ros2_ws/install/setup.bash
ros2 launch model_description full_robot.launch.py
```

O launch inicia o Gazebo, publica o URDF, cria o robô e ativa:

- `joint_state_broadcaster`
- `diff_drive_base_controller`

O teleop fica desativado por padrão. Para iniciar o teclado, use:

```bash
ros2 launch model_description full_robot.launch.py teleop:=true
```

Não execute teleop junto com os nós de missão ou trajetória, pois todos publicam comandos de velocidade.

Verifique os controladores:

```bash
ros2 control list_controllers
```

Resultado esperado:

```text
diff_drive_base_controller active
joint_state_broadcaster active
```

Verifique a odometria:

```bash
ros2 topic echo /diff_drive_base_controller/odom --once
```

## Exercício 1.1 — Controle de pose contínuo

O nó é `pose_control_node`. Ele recebe uma meta em `/goal_pose`, lê a odometria e publica `Twist` em `/cmd_vel`. O launch remapeia esses tópicos para o controlador do Gazebo.

Com o Gazebo rodando, execute:

```bash
source /opt/ros/humble/setup.bash
source ~/ros2_ws/install/setup.bash
ros2 launch meu_robo_control mission.launch.py
```

Esse launch inicia o controlador de pose e o `mission_node`. Para testar apenas o controlador, execute:

```bash
ros2 run meu_robo_control pose_control_node --ros-args \
  -p use_sim_time:=true \
  -r /odom:=/diff_drive_base_controller/odom \
  -r /cmd_vel:=/diff_drive_base_controller/cmd_vel_unstamped
```

Em outro terminal, publique uma meta:

```bash
ros2 topic pub --once /goal_pose geometry_msgs/msg/PoseStamped \
  "{header: {frame_id: odom}, pose: {position: {x: 1.0, y: 0.0, z: 0.0}, orientation: {w: 1.0}}}"
```

Observe os comandos gerados:

```bash
ros2 topic echo /diff_drive_base_controller/cmd_vel_unstamped
```

Os ganhos e limites do controlador estão em:

```text
src/model_description/model_description/src/meu_robo_control/config/controller_params.yaml
```

O controlador atual é proporcional com saturação de velocidade. Para cumprir estritamente a exigência de uma biblioteca PID, é necessário substituir ou estender essa implementação com um controlador PID e documentar seus ganhos no YAML.

## Exercício 1.1 — Bônus: três manobras

O projeto atual não possui um nó separado para a sequência rotação–translação–rotação. Essa parte deve ser implementada como uma máquina de estados que:

1. gira até o ângulo do ponto;
2. avança até a posição;
3. gira até a orientação final.

Depois de implementada, ela deve publicar no mesmo `cmd_vel` com um launch separado para poder ser comparada ao controle contínuo.

## Exercício 1.2 — Seguimento de missão

Os waypoints estão em:

```text
src/model_description/model_description/src/meu_robo_control/config/waypoints.yaml
```

O arquivo atual contém quatro pontos:

```text
(0, 0, 0)
(2, 0, 1.57)
(2, 2, 3.14)
(0, 2, 0)
```

Execute:

```bash
ros2 launch meu_robo_control mission.launch.py
```

O `mission_node` publica cada ponto em `/goal_pose` e só avança quando o robô entra no raio `acc_rad`:

```bash
ros2 topic echo /goal_pose
```

Para acompanhar a posição real:

```bash
ros2 topic echo /diff_drive_base_controller/odom
```

O valor `acc_rad` é uma tolerância em metros. Um valor típico é `0.15`; ele não controla a velocidade.

## Exercício 2.1 — Trajetória em oito

O nó `trajectory_node` gera a trajetória paramétrica:

```text
x_d(t) = A sin(Ωt)
y_d(t) = (B/2) sin(2Ωt)
```

Os valores padrão são `A = 1.0`, `B = 2.0` e `Ω = 0.5`. A execução usa o launch:

```bash
ros2 launch meu_robo_control trajectory.launch.py
```

O nó possui os modos:

- `open_loop:=true`: somente feedforward;
- `open_loop:=false`: realimentação com termo feedforward ponderado por `k_ff`.

Exemplo de malha aberta:

```bash
ros2 run meu_robo_control trajectory_node --ros-args \
  -p use_sim_time:=true \
  -p open_loop:=true \
  -p A:=1.0 -p B:=2.0 -p omega:=0.5 \
  -r /odom:=/diff_drive_base_controller/odom \
  -r /cmd_vel:=/diff_drive_base_controller/cmd_vel_unstamped
```

Exemplo realimentado sem feedforward (`Kff = 0`):

```bash
ros2 run meu_robo_control trajectory_node --ros-args \
  -p use_sim_time:=true \
  -p open_loop:=false -p k_ff:=0.0 \
  -r /odom:=/diff_drive_base_controller/odom \
  -r /cmd_vel:=/diff_drive_base_controller/cmd_vel_unstamped
```

Exemplo realimentado com feedforward (`Kff = 1`):

```bash
ros2 run meu_robo_control trajectory_node --ros-args \
  -p use_sim_time:=true \
  -p open_loop:=false -p k_ff:=1.0 \
  -r /odom:=/diff_drive_base_controller/odom \
  -r /cmd_vel:=/diff_drive_base_controller/cmd_vel_unstamped
```

O nó limita os comandos a `0.6 m/s` e `1.5 rad/s`. A publicação de uma referência em `/ref_pose` deve ser adicionada ao nó para permitir a comparação automática da trajetória desejada e real no PlotJuggler.

## Exercício 2.2 — PlotJuggler

Instale o PlotJuggler, se necessário:

```bash
sudo apt update
sudo apt install ros-humble-plotjuggler-ros
```

Inicie-o antes da missão ou trajetória:

```bash
source /opt/ros/humble/setup.bash
source ~/ros2_ws/install/setup.bash
ros2 run plotjuggler plotjuggler
```

Na seção `Streaming`, selecione `ROS2 Topic Subscriber`, clique em `Start` e adicione:

```text
/diff_drive_base_controller/odom
/goal_pose
/diff_drive_base_controller/cmd_vel_unstamped
/ref_pose
```

Para a missão, compare:

```text
/diff_drive_base_controller/odom → pose → pose → position → x/y
/goal_pose → pose → position → x/y
```

Para a trajetória, compare a odometria com `/ref_pose`. Se `/ref_pose` não aparecer, a referência ainda não está sendo publicada pelo `trajectory_node`.

## Bônus — RMSE

Colete os dados de cada execução no PlotJuggler ou em um rosbag e calcule:

```text
RMSE = sqrt(mean((x_real - x_desejado)^2 + (y_real - y_desejado)^2))
```

Repita para:

1. malha aberta;
2. realimentação com `k_ff = 0`;
3. realimentação com `k_ff = 1`.

Use exatamente os mesmos valores de `A`, `B`, `omega` e o mesmo tempo de execução para que a comparação seja válida.

## Diagnóstico rápido

```bash
ros2 node list
ros2 topic list
ros2 topic info /diff_drive_base_controller/odom
ros2 topic info /diff_drive_base_controller/cmd_vel_unstamped
ros2 control list_controllers
```

Se o robô não aparecer, encerre instâncias antigas e inicie novamente:

```bash
pkill -f gzclient
pkill -f gzserver
ros2 launch model_description full_robot.launch.py
```

## Prática 04 — Sensores

### Exercício 1.1 — Adicionar sensores

O URDF agora inclui quatro sensores Gazebo ROS 2, cada um com um link visual próprio:

| Sensor | Link visual | Tópico | Tipo de mensagem | Frequência |
|---|---|---|---|---:|
| IMU | `imu_link` | `/imu/data` | `sensor_msgs/msg/Imu` | 100 Hz |
| GPS | `gps_link` | `/gps/fix` | `sensor_msgs/msg/NavSatFix` | 10 Hz |
| Câmera RGB frontal | `camera_link` | `/camera/image_raw` | `sensor_msgs/msg/Image` | 30 Hz |
| Câmera RGB frontal | `camera_link` | `/camera/camera_info` | `sensor_msgs/msg/CameraInfo` | 30 Hz |
| Lidar 2D frontal | `lidar_link` | `/scan` | `sensor_msgs/msg/PointCloud2` | 15 Hz |

Os sensores aparecem no robô como caixas coloridas: IMU azul, GPS amarelo, câmera preta e lidar verde. O Gazebo também mostra os feixes dos sensores quando `visualize` está habilitado.

Todos os sensores possuem ruído gaussiano configurado no URDF:

- IMU: ruído separado para orientação, velocidade angular e aceleração linear;
- GPS: ruído horizontal e vertical em metros;
- câmera: ruído gaussiano de imagem;
- lidar: ruído gaussiano nas distâncias.

### Verificar os sensores

Compile novamente o pacote depois de alterar o URDF:

```bash
source /opt/ros/humble/setup.bash
cd ~/ros2_ws
colcon build \
  --base-paths src/model_description/model_description \
  --packages-select model_description \
  --symlink-install
source install/setup.bash
```

Reinicie o Gazebo para recarregar o modelo:

```bash
pkill -f gzclient
pkill -f gzserver
ros2 launch model_description full_robot.launch.py
```

Liste os tópicos dos sensores:

```bash
ros2 topic list | grep -E '/imu|/gps|/camera|/scan'
```

Confira os tipos:

```bash
ros2 topic type /imu/data
ros2 topic type /gps/fix
ros2 topic type /camera/image_raw
ros2 topic type /camera/camera_info
ros2 topic type /scan
```

Veja uma medição de cada sensor:

```bash
ros2 topic echo /imu/data --once
ros2 topic echo /gps/fix --once
ros2 topic echo /camera/camera_info --once
ros2 topic echo /scan --once
```

Para visualizar a imagem RGB, instale e execute o `rqt_image_view`:

```bash
sudo apt install ros-humble-rqt-image-view
ros2 run rqt_image_view rqt_image_view
```

Na janela, selecione `/camera/image_raw`. Para visualizar o PointCloud2 do lidar no RViz2:

```bash
rviz2
```

Adicione displays `Image` e `PointCloud2`, usando respectivamente `/camera/image_raw` e `/scan`.

### Exercício 1.2 — Visualização dos dados dos sensores

#### PlotJuggler — IMU e GPS

Com o Gazebo e os sensores em execução, abra o PlotJuggler:

```bash
source /opt/ros/humble/setup.bash
source ~/ros2_ws/install/setup.bash
ros2 run plotjuggler plotjuggler
```

Na seção `Streaming`, selecione `ROS2 Topic Subscriber`, clique em `Start` e adicione:

```text
/imu/data
/gps/fix
```

No tópico `/imu/data`, visualize:

```text
orientation → x, y, z, w
angular_velocity → x, y, z
linear_acceleration → x, y, z
```

No tópico `/gps/fix`, visualize:

```text
latitude
longitude
altitude
position_covariance[0]
position_covariance[4]
position_covariance[8]
```

Para confirmar as frequências de publicação:

```bash
ros2 topic hz /imu/data
ros2 topic hz /gps/fix
```

#### RViz2 — câmera RGB e lidar

Abra o RViz2:

```bash
source /opt/ros/humble/setup.bash
source ~/ros2_ws/install/setup.bash
rviz2
```

Configure `Fixed Frame` como `base_link`. Adicione um display `Image` com o tópico:

```text
/camera/image_raw
```

Esse display mostra a imagem RGB frontal. Adicione um display `PointCloud2` com:

```text
/scan
```

Use `Style: Points` e um tamanho de ponto aproximado de `0.03`. O lidar deve aparecer como uma nuvem de pontos no arco frontal do robô.

Verifique os tipos e frequências:

```bash
ros2 topic type /camera/image_raw
ros2 topic type /scan
ros2 topic hz /camera/image_raw
ros2 topic hz /scan
```

Os tipos esperados são `sensor_msgs/msg/Image` e `sensor_msgs/msg/PointCloud2`. Se os sensores não aparecerem na posição correta, adicione um display `TF` e confira os frames `base_link`, `camera_link` e `lidar_link`.

Para converter a posição global do GPS para coordenadas locais `(X,Y,Z)`, use a origem geográfica como referência e aplique a aproximação local:

```text
X ≈ (longitude - longitude_0) · cos(latitude_0) · R
Y ≈ (latitude  - latitude_0) · R
Z = altitude - altitude_0
```

com os ângulos em radianos e `R = 6378137 m`. O nó `gps_to_local_node` já realiza essa conversão e publica `geometry_msgs/msg/PointStamped` em `/gps/position_local`.

Para executá-lo, escolha a origem geográfica do seu cenário. Por exemplo:

```bash
ros2 run meu_robo_control gps_to_local_node --ros-args \
  -p use_sim_time:=true \
  -p origin_latitude:=-23.550520 \
  -p origin_longitude:=-46.633308 \
  -p origin_altitude:=760.0
```

Ou use o arquivo de parâmetros e o launch:

```bash
ros2 launch meu_robo_control gps.launch.py
```

Edite `config/gps_params.yaml` antes de iniciar para colocar a latitude, longitude e altitude da origem. O resultado pode ser verificado com:

```bash
ros2 topic type /gps/position_local
ros2 topic echo /gps/position_local
```

Nesse frame ENU local, `X` é Leste, `Y` é Norte e `Z` é altitude relativa à origem, todos em metros.


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

O workspace consolidado usa um único pacote ROS 2: `meu_robo_control`.
Ele contém o URDF, Gazebo, sensores, controllers, pose, missão, manobras, GPS,
EKF, trajetória e RMSE.

Compile somente esse pacote a partir de `~/ros2_ws`:

```bash
source /opt/ros/humble/setup.bash
cd ~/ros2_ws

colcon --log-base /tmp/ros2_ws_colcon_logs build \
  --base-paths src/model_description/model_description/src/meu_robo_control \
  --packages-select meu_robo_control \
  --symlink-install

source install/setup.bash
```

Confirme a instalação:

```bash
ros2 pkg executables meu_robo_control
ls install/meu_robo_control/share/meu_robo_control/urdf/robot_no_noise.urdf
ls install/meu_robo_control/share/meu_robo_control/config/trajectory_params.yaml
```

## Inicialização do Gazebo

Em um terminal, inicie o mundo padrão, o robô `meu_robo` e os controllers:

```bash
source /opt/ros/humble/setup.bash
source ~/ros2_ws/install/setup.bash
ros2 launch meu_robo_control full_robot.launch.py
```

Por padrão, o robô é iniciado com ruído nos sensores. Para iniciar sem ruído:

```bash
ros2 launch meu_robo_control full_robot.launch.py sensor_noise:=false
```

O launch inicia o Gazebo, publica o URDF, cria o robô e ativa:

- `joint_state_broadcaster`
- `diff_drive_base_controller`

O teleop fica desativado por padrão. Para iniciar o teclado, use:

```bash
ros2 launch meu_robo_control full_robot.launch.py teleop:=true
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

Após essa etapa, execute somente um controlador de movimento por vez. Por
exemplo, para a trajetória em oito:

```bash
ros2 launch meu_robo_control trajectory.launch.py
```

Para a trajetória com fusão opcional de sensores:

```bash
ros2 launch meu_robo_control trajectory_estimated.launch.py \
  use_sensor_fusion:=true
```

Sem influência dos sensores, usando a odometria direta:

```bash
ros2 launch meu_robo_control trajectory_estimated.launch.py \
  use_sensor_fusion:=false
```

### Alternativa para WSL ou problemas gráficos

Se a janela do Gazebo ficar preta, vazia, o `gzclient` fechar ou houver mais de
uma instância antiga do servidor, use primeiro este ambiente:

```bash
source /opt/ros/humble/setup.bash
source ~/ros2_ws/install/setup.bash

export ROS_LOCALHOST_ONLY=1
export GAZEBO_IP=127.0.0.1
export GAZEBO_MASTER_URI=http://127.0.0.1:11345
export LIBGL_ALWAYS_SOFTWARE=1
export LIBGL_DRI3_DISABLE=1
export MESA_GL_VERSION_OVERRIDE=3.3
export ROS_LOG_DIR=/tmp/ros_logs
export GAZEBO_LOG_PATH=/tmp/gazebo_logs

mkdir -p "$ROS_LOG_DIR" "$GAZEBO_LOG_PATH" "$HOME/.gazebo"

pkill -x gzclient 2>/dev/null || true
pkill -x gzserver 2>/dev/null || true
pkill -x spawner 2>/dev/null || true
```

Inicie somente o servidor Gazebo e o robô, sem a interface gráfica:

```bash
source /opt/ros/humble/setup.bash
source ~/ros2_ws/install/setup.bash

ros2 launch meu_robo_control full_robot.launch.py \
  world:=$(ros2 pkg prefix meu_robo_control)/share/meu_robo_control/worlds/slam_large.world \
  gui:=false \
  sensor_noise:=false
```

O terminal deve informar que o robô foi criado e que os dois controllers foram
ativados. Em outro terminal, abra apenas o cliente gráfico com renderização por
software:

```bash
source /opt/ros/humble/setup.bash
source ~/ros2_ws/install/setup.bash
export GAZEBO_MASTER_URI=http://127.0.0.1:11345
export LIBGL_ALWAYS_SOFTWARE=1
export LIBGL_DRI3_DISABLE=1
export MESA_GL_VERSION_OVERRIDE=3.3

gzclient --verbose
```

O `gzclient` deve ser iniciado em um segundo terminal, mantendo o mesmo
`GAZEBO_MASTER_URI` do `gzserver`. Se a renderização continuar indisponível,
use somente o primeiro terminal com `gui:=false`; o Gazebo, os controllers, os
sensores e o SLAM continuarão funcionando sem a interface gráfica.

Se quiser testar com ruído, troque `sensor_noise:=false` por:

```bash
sensor_noise:=true
```

Para testar apenas o servidor e ignorar completamente o OpenGL, mantenha o
`gui:=false` e verifique em outro terminal:

```bash
ros2 service list | grep spawn
ros2 control list_controllers
ros2 topic info /diff_drive_base_controller/odom -v
```

Confirme que há somente um servidor ativo:

```bash
pgrep -af 'gzserver|gzclient'
```

Se o comando retornar mais de um processo, encerre as instâncias antigas e repita o procedimento. Essa alternativa separa problemas do servidor Gazebo de problemas de renderização do `gzclient` no WSLg.

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

Os ganhos PID e limites do controlador estão em:

```text
src/model_description/model_description/src/meu_robo_control/config/controller_params.yaml
```

O controlador usa a classe `PID` do módulo reutilizável `meu_robo_control/pid_controller.py`. Ela implementa termos proporcional, integral e derivativo, limites de saída e anti-windup. Os valores `kp_*`, `ki_*` e `kd_*` são carregados do YAML pelo `pose_control_node`.

## Exercício 1.1 — Bônus: três manobras

O nó `maneuver_pose_node` executa cada meta como uma máquina de estados:

1. gira até apontar para o waypoint;
2. avança até a posição;
3. gira até a orientação final.

Compile os pacotes, se necessário:

```bash
source /opt/ros/humble/setup.bash
cd ~/ros2_ws

colcon build \
  --base-paths src/model_description/model_description/src/meu_robo_control \
  --packages-select meu_robo_control \
  --symlink-install

colcon build \
  --base-paths src/model_description/model_description/src/meu_robo_control \
  --packages-select meu_robo_control \
  --symlink-install

source install/setup.bash
```

Em um primeiro terminal, inicie o Gazebo e os controladores:

```bash
source /opt/ros/humble/setup.bash
source ~/ros2_ws/install/setup.bash
ros2 launch meu_robo_control full_robot.launch.py
```

Confirme que os controladores estão ativos:

```bash
ros2 control list_controllers
```

O resultado esperado contém:

```text
diff_drive_base_controller active
joint_state_broadcaster active
```

Em um segundo terminal, execute a missão com o controlador de três manobras:

```bash
source /opt/ros/humble/setup.bash
source ~/ros2_ws/install/setup.bash
ros2 launch meu_robo_control maneuver_mission.launch.py
```

Os waypoints são carregados de `config/waypoints.yaml`. Para acompanhar os comandos enviados:

```bash
ros2 topic echo /diff_drive_base_controller/cmd_vel_unstamped
```

O terminal do `maneuver_pose_node` informa as transições entre `rotate_initial`, `translate` e `rotate_final`. Não execute `mission.launch.py`, teleop ou `trajectory.launch.py` ao mesmo tempo, pois todos podem publicar comandos no mesmo controlador.

Os parâmetros estão em `config/maneuver_params.yaml`. O nó publica no mesmo controlador diferencial, portanto não deve ser executado junto com `mission.launch.py` ou com `trajectory.launch.py`.

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

### (Bônus) Compare o seguimento de uma missão usando o controle de pose com três manobras e o contínuo

Execute a mesma missão duas vezes, sempre iniciando o robô na mesma pose e usando o mesmo `waypoints.yaml`.

| Critério | Controle contínuo | Três manobras |
|---|---|---|
| Suavidade | Maior | Menor |
| Paradas entre pontos | Poucas ou nenhuma | Rotação e translação separadas |
| Facilidade de implementação | Média | Alta |
| Precisão da orientação final | Depende dos ganhos PID | Controlada explicitamente |
| Adequação para trajetória em oito | Melhor | Inadequada |
| Adequação para waypoints discretos | Boa | Boa |
| Velocidade do percurso | Geralmente maior | Geralmente menor |
| Sensibilidade aos ganhos | Maior | Menor |

Controle contínuo:

```bash
ros2 launch meu_robo_control mission.launch.py
```

Controle com três manobras:

```bash
ros2 launch meu_robo_control maneuver_mission.launch.py
```

Não execute os dois ao mesmo tempo. Compare no PlotJuggler:

```text
/diff_drive_base_controller/odom/pose/pose/position/x
/diff_drive_base_controller/odom/pose/pose/position/y
/diff_drive_base_controller/odom/twist/twist/linear/x
/diff_drive_base_controller/odom/twist/twist/angular/z
```

Os principais critérios experimentais são o tempo total da missão, o erro de posição e orientação em cada waypoint, a velocidade máxima, a distância percorrida, a quantidade de paradas e a suavidade dos comandos.

## Prática — Filtro de Kalman e controle usando estado estimado

### Exercício 1.1 — Estimando estados com o filtro de Kalman

Foi adicionada uma configuração do `robot_localization` com um filtro EKF em duas dimensões. O filtro combina:

- odometria das rodas em `/diff_drive_base_controller/odom`;
- orientação e velocidade angular da IMU em `/imu/data`.

O estado estimado é publicado em:

```text
/odometry/filtered
```

Ele contém a pose estimada `(x, y, yaw)` e as velocidades filtradas. A configuração está em:

```text
src/model_description/model_description/src/meu_robo_control/config/ekf.yaml
```

Compile o pacote de controle:

```bash
source /opt/ros/humble/setup.bash
cd ~/ros2_ws
colcon build \
  --base-paths src/model_description/model_description/src/meu_robo_control \
  --packages-select meu_robo_control \
  --symlink-install
source install/setup.bash
```

Com o Gazebo e os controladores em execução, inicie o EKF em outro terminal:

```bash
source /opt/ros/humble/setup.bash
source ~/ros2_ws/install/setup.bash
ros2 launch meu_robo_control ekf.launch.py
```

Verifique a publicação e a taxa:

```bash
ros2 topic type /odometry/filtered
ros2 topic hz /odometry/filtered
ros2 topic echo /odometry/filtered --once
```

O tipo esperado é `nav_msgs/msg/Odometry`. Para observar os dados usados pelo filtro:

```bash
ros2 topic hz /diff_drive_base_controller/odom
ros2 topic hz /imu/data
```

O pacote `robot_localization` precisa estar instalado:

```bash
sudo apt update
sudo apt install ros-humble-robot-localization
```

### Exercício 2.1 — Trajetória em oito usando o estado estimado

Foi criado o launch `trajectory_estimated.launch.py`, que inicia o EKF e remapeia a entrada de odometria do `trajectory_node` para `/odometry/filtered`.

O experimento final deverá comparar no PlotJuggler:

```text
Estado real: ground truth publicado pelo Gazebo
Estado bruto: /diff_drive_base_controller/odom
Estado estimado: /odometry/filtered
Trajetória desejada: /ref_pose ou /trajectory_reference
```

Para executar a trajetória com o estado estimado:

```bash
ros2 launch meu_robo_control trajectory_estimated.launch.py
```

O launch normal continua usando a odometria bruta para comparação:

```bash
ros2 launch meu_robo_control trajectory.launch.py
```

Para aumentar o ruído, ajuste os valores `stddev` das tags de ruído da IMU, GPS, câmera ou lidar em `urdf/robot.urdf`, recompile `meu_robo_control` e reinicie o Gazebo. Registre os quatro estados no PlotJuggler para comparar o efeito do ruído e da filtragem.

Para o experimento temporário com ruído aumentado, o URDF está usando atualmente:

```text
IMU orientação:             stddev = 0.03
IMU velocidade angular:     stddev = 0.08
IMU aceleração linear:      stddev = 0.15
GPS horizontal:             stddev = 3.0 m
GPS vertical:               stddev = 5.0 m
```

Recompile e reinicie a simulação para aplicar o perfil:

```bash
source /opt/ros/humble/setup.bash
cd ~/ros2_ws
colcon build \
  --base-paths src/model_description/model_description/src/meu_robo_control \
  --packages-select meu_robo_control \
  --symlink-install
source install/setup.bash
```

Depois compare no PlotJuggler:

```text
Estado bruto:    /diff_drive_base_controller/odom
Estado estimado: /odometry/filtered
Referência:      /ref_pose ou /trajectory_reference
```

O EKF atual usa a odometria e a IMU. O GPS está com ruído aumentado para visualização, mas ainda não está incluído como entrada do EKF. Para retornar ao perfil original, restaure os `stddev` anteriores definidos na seção de sensores deste arquivo.

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

O nó limita os comandos a `0.6 m/s` e `1.5 rad/s`. Ele publica a referência instantânea em `/ref_pose` para o PlotJuggler e o histórico acumulado em `/trajectory_reference` (`nav_msgs/msg/Path`) para o RViz2.

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

Para a trajetória, compare a odometria com `/ref_pose` no PlotJuggler ou use `/trajectory_reference` no display `Path` do RViz2.

### Visualizar a trajetória em oito no RViz2

O `trajectory_node` publica o histórico da referência desejada em:

```text
/trajectory_reference
```

Esse tópico usa `nav_msgs/msg/Path` e desenha o oito diretamente no RViz2.

Inicie o Gazebo e a trajetória:

```bash
source /opt/ros/humble/setup.bash
source ~/ros2_ws/install/setup.bash

ros2 launch meu_robo_control full_robot.launch.py
```

Em outro terminal:

```bash
source /opt/ros/humble/setup.bash
source ~/ros2_ws/install/setup.bash

ros2 launch meu_robo_control trajectory.launch.py
```

Confirme a publicação:

```bash
ros2 topic type /trajectory_reference
ros2 topic hz /trajectory_reference
```

Os resultados esperados são `nav_msgs/msg/Path` e aproximadamente 20 Hz.

Abra o RViz2:

```bash
rviz2
```

Se a área 3D do RViz2 ficar preta, especialmente no WSLg, feche instâncias antigas e inicie o RViz2 com renderização por software:

```bash
pkill -f rviz2

source /opt/ros/humble/setup.bash
source ~/ros2_ws/install/setup.bash
export LIBGL_ALWAYS_SOFTWARE=1
export LIBGL_DRI3_DISABLE=1
export MESA_GL_VERSION_OVERRIDE=3.3

rviz2
```

Se a configuração anterior estiver corrompida, inicie com uma configuração limpa, preservando o backup:

```bash
mv ~/.rviz2 /tmp/rviz2_backup
rviz2
```

Configure `Global Options` com:

```text
Fixed Frame: odom
```

Depois clique em `Add`, escolha `By display type` e adicione `Path`. No campo `Topic`, selecione:

```text
/trajectory_reference
```

Defina `Alpha` como `1.0`, escolha uma cor visível e use `Line Width` próximo de `0.03`. Adicione também um display `Grid`, selecione `Plane: XY` e use `Cell Size: 1`. Para centralizar, clique com o botão direito na área 3D e escolha `Focus Camera`.

O display `Path` mostra o oito desejado no plano XY. A odometria real continua disponível em `/diff_drive_base_controller/odom` e pode ser comparada no PlotJuggler.

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
ros2 launch meu_robo_control full_robot.launch.py
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
  --base-paths src/model_description/model_description/src/meu_robo_control \
  --packages-select meu_robo_control \
  --symlink-install
source install/setup.bash
```

Reinicie o Gazebo para recarregar o modelo:

```bash
pkill -f gzclient
pkill -f gzserver
ros2 launch meu_robo_control full_robot.launch.py
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

## Trajetória em oito e uso opcional dos sensores

O ruído dos sensores também é opcional no launch do Gazebo. O arquivo
`robot.urdf` mantém os níveis de ruído configurados; `robot_no_noise.urdf` usa
os mesmos sensores com desvio padrão zero.

Para iniciar o robô com ruído, que é o padrão:

```bash
ros2 launch meu_robo_control full_robot.launch.py sensor_noise:=true
```

Para iniciar o robô sem ruído:

```bash
ros2 launch meu_robo_control full_robot.launch.py sensor_noise:=false
```

O mesmo argumento está disponível no launch básico:

```bash
ros2 launch meu_robo_control gazebo.launch.py sensor_noise:=false
```

Essa opção escolhe o URDF no momento da criação do robô. Portanto, encerre a
simulação atual e inicie uma nova para alternar entre os modos.

O controlador da trajetória em oito está em `trajectory_node`. Os parâmetros da
trajetória e do controlador ficam em:

```text
src/model_description/model_description/src/meu_robo_control/config/trajectory_params.yaml
```

Inicie a trajetória usando a odometria direta do controlador diferencial:

```bash
ros2 launch meu_robo_control trajectory.launch.py
```

Nesse modo, a pose usada pelo controlador vem de:

```text
/diff_drive_base_controller/odom
```

A IMU, o GPS, a câmera e o lidar não influenciam diretamente o controle.

Para executar a versão com fusão de sensores pelo `robot_localization`/EKF:

```bash
ros2 launch meu_robo_control trajectory_estimated.launch.py \
  use_sensor_fusion:=true
```

Nesse modo, a IMU e a odometria são combinadas pelo EKF, e o controlador usa:

```text
/odometry/filtered
```

Para executar o mesmo launch sem influência dos sensores, usando novamente a
odometria direta:

```bash
ros2 launch meu_robo_control trajectory_estimated.launch.py \
  use_sensor_fusion:=false
```

Resumo dos modos:

| Comando | Pose usada pelo controlador | Sensores influenciam? |
|---|---|---|
| `trajectory.launch.py` | `/diff_drive_base_controller/odom` | Não |
| `trajectory_estimated.launch.py use_sensor_fusion:=false` | `/diff_drive_base_controller/odom` | Não |
| `trajectory_estimated.launch.py use_sensor_fusion:=true` | `/odometry/filtered` | Sim, via EKF |

Durante a execução, compare os tópicos:

```bash
ros2 topic info /imu/data -v
ros2 topic info /diff_drive_base_controller/odom -v
ros2 topic info /odometry/filtered -v
ros2 topic echo /ref_pose
ros2 topic echo /real_pose
```

Para calcular o RMSE da trajetória, execute em outro terminal:

```bash
ros2 run meu_robo_control rmse_node
```

Não execute `trajectory.launch.py`, `trajectory_estimated.launch.py`,
`mission.launch.py` e `maneuver_mission.launch.py` ao mesmo tempo, pois eles
podem publicar comandos simultaneamente em `/cmd_vel`.

## SLAM 2D e experimentos de ruído

O Lidar 2D publica `sensor_msgs/LaserScan` em `/lidar_plugin/out` (tópico
efetivamente gerado pelo plugin do Gazebo). O URDF
`robot_no_noise.urdf` usa medições ideais; `robot.urdf` aplica ruído gaussiano
ao Lidar. A odometria do controlador é relativa e ground truth do Gazebo. Para
simular erro de dead reckoning, `odom_noise_node` adiciona ruído aos incrementos
de odometria, sem usar GPS ou qualquer referência absoluta.

Instale o SLAM Toolbox caso ainda não esteja disponível:

```bash
sudo apt update
sudo apt install ros-humble-slam-toolbox
```

Use o cenário ampliado, com paredes externas e obstáculos distribuídos:

Sempre reinicie os processos nesta ordem. Isso evita que o `slam_toolbox` use
um relógio ou uma árvore TF antiga:

```bash
pkill -f rviz2
pkill -f explorer_node
pkill -f slam_toolbox
pkill -f gzserver
pkill -f ros2.launch
```

1. Inicie o Gazebo e o robô:

```bash
source /opt/ros/humble/setup.bash
source ~/ros2_ws/install/setup.bash

ros2 launch meu_robo_control full_robot.launch.py \
  world:=$(ros2 pkg prefix meu_robo_control)/share/meu_robo_control/worlds/slam_large.world \
  sensor_noise:=false \
  gui:=false
```

2. Em um segundo terminal, inicie o SLAM:

```bash
source /opt/ros/humble/setup.bash
source ~/ros2_ws/install/setup.bash

ros2 launch meu_robo_control slam.launch.py odom_noise:=true
```

3. Em um terceiro terminal, inicie a exploração autônoma:

```bash
source /opt/ros/humble/setup.bash
source ~/ros2_ws/install/setup.bash

ros2 launch meu_robo_control explorer.launch.py
```

4. Somente depois abra o RViz2:

```bash
source /opt/ros/humble/setup.bash
source ~/ros2_ws/install/setup.bash

rviz2
```

No RViz2, configure `Fixed Frame` como `map` e adicione `/map`,
`/lidar_plugin/out`, `TF` e `RobotModel`. Verifique a árvore antes de iniciar
o experimento:

```bash
ros2 run tf2_ros tf2_echo map base_link
```

Deve existir continuamente a cadeia:

```text
map -> odom -> base_link -> lidar_link
```

Para comparar os três casos, mantenha a mesma ordem acima e altere apenas os
parâmetros:

```bash
# 1) Lidar ideal + odometria ground truth
sensor_noise:=false
ros2 launch meu_robo_control slam.launch.py odom_noise:=false

# 2) Lidar ruidoso + odometria ground truth
# reinicie o Gazebo com sensor_noise:=true:
ros2 launch meu_robo_control slam.launch.py odom_noise:=false

# 3) Lidar ruidoso + odometria ruidosa
ros2 launch meu_robo_control slam.launch.py odom_noise:=true
```

Nos casos 2 e 3, `sensor_noise:=true` deve ser usado ao iniciar o Gazebo. O
caso 3 publica a odometria relativa ruidosa em `/odom_noisy`. O SLAM publica o
mapa em `/map` e a transformação `map -> odom`.

Para salvar o mapa construído:

```bash
ros2 run nav2_map_server map_saver_cli -f ~/mapa_slam
```

### Exploração autônoma

O `explorer_node` movimenta o robô sem teclado usando somente o Lidar 2D. Ele
avança, detecta obstáculos, gira para o lado com maior espaço e publica em
`/diff_drive_base_controller/cmd_vel_unstamped`.

Com o Gazebo e o SLAM já iniciados, execute:

```bash
ros2 launch meu_robo_control explorer.launch.py
```

Ou diretamente:

```bash
ros2 run meu_robo_control explorer_node \
  --ros-args \
  --params-file $(ros2 pkg prefix meu_robo_control)/share/meu_robo_control/config/explorer_params.yaml
```

Para interromper o mapeamento, use `Ctrl+C`; o nó envia velocidade zero ao
finalizar. O mapa é atualizado enquanto o robô percorre o cenário.

### Robô sequestrado

Com o caso 3 em execução e o mapa visível no RViz, pause o Gazebo pelo botão
Pause. Selecione o modelo `meu_robo` na interface, use a ferramenta de
translação e mova-o para o outro lado do mapa. Retome a simulação. O SLAM deve
relocalizar o robô por correspondência entre `/lidar_plugin/out` e o mapa; a recuperação é
avaliada observando a transformação `map -> odom`, não uma posição GPS.


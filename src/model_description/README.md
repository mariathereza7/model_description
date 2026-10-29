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

### Alternativa para WSL ou problemas gráficos

Se a janela do Gazebo ficar preta, vazia ou se houver mais de uma instância antiga do servidor, encerre os processos antes de iniciar:

```bash
pkill -f gzclient
pkill -f gzserver
pkill -f spawner
```

Inicie somente o servidor Gazebo, sem a interface gráfica:

```bash
source /opt/ros/humble/setup.bash
source ~/ros2_ws/install/setup.bash

ros2 launch model_description full_robot.launch.py gui:=false
```

O terminal deve informar que o robô foi criado e que os dois controladores foram ativados. Em outro terminal, abra apenas o cliente gráfico com renderização por software:

```bash
source /opt/ros/humble/setup.bash
export GAZEBO_MASTER_URI=http://localhost:11345
export LIBGL_ALWAYS_SOFTWARE=1

gzclient --verbose
```

Confirme que há somente um servidor ativo:

```bash
pgrep -af gzserver
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
  --base-paths src/model_description/model_description \
  --packages-select model_description \
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
ros2 launch model_description full_robot.launch.py
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

ros2 launch model_description full_robot.launch.py
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


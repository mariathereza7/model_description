# Roteiro de demonstração — `meu_robo_control`

Todos os experimentos usam odometria relativa. GPS não é usado para corrigir a pose.

## Preparação

```bash
cd ~/ros2_ws
source /opt/ros/humble/setup.bash
colcon build --base-paths src/model_description/model_description/src/meu_robo_control --packages-select meu_robo_control --symlink-install
source install/setup.bash
sudo apt install ros-humble-slam-toolbox
```

Para reiniciar uma demonstração:

```bash
pkill -f rviz2 || true
pkill -f explorer_node || true
pkill -f slam_toolbox || true
pkill -f gzserver || true
pkill -f ros2.launch || true
```

## 1. Sensores e ruído

O Lidar 2D publica `sensor_msgs/msg/LaserScan` em `/lidar_plugin/out`.

```bash
ros2 topic hz /lidar_plugin/out
ros2 topic echo /imu_plugin/out --once
```

Use `sensor_noise:=false` para medições ideais e `sensor_noise:=true` para
ruído no Lidar, IMU e demais sensores configurados no URDF.

## 2. SLAM e exploração autônoma

O mundo usado é `slam_large.world`, com paredes e obstáculos distribuídos.
A ordem de inicialização é obrigatória.

Antes de começar, encerre instâncias antigas:

```bash
pkill -f rviz2 || true
pkill -f explorer_node || true
pkill -f slam_toolbox || true
pkill -f gzserver || true
pkill -f ros2.launch || true
```

Em todos os terminais, carregue o mesmo ambiente:

```bash
source /opt/ros/humble/setup.bash
source ~/ros2_ws/install/setup.bash
```

### Terminal 1 — Gazebo

```bash
source /opt/ros/humble/setup.bash
source ~/ros2_ws/install/setup.bash
ros2 launch meu_robo_control full_robot.launch.py \
  world:=$(ros2 pkg prefix meu_robo_control)/share/meu_robo_control/worlds/slam_large.world \
  sensor_noise:=true gui:=false
```

### Terminal 2 — SLAM Toolbox

```bash
source /opt/ros/humble/setup.bash
source ~/ros2_ws/install/setup.bash
ros2 launch meu_robo_control slam.launch.py odom_noise:=true
```

### Terminal 3 — exploração

```bash
source /opt/ros/humble/setup.bash
source ~/ros2_ws/install/setup.bash
ros2 launch meu_robo_control explorer.launch.py
```

### Terminal 4 — RViz2

```bash
source /opt/ros/humble/setup.bash
source ~/ros2_ws/install/setup.bash
rviz2
```

No RViz2, use `Fixed Frame: map` e adicione `Map: /map`, `LaserScan:
/lidar_plugin/out`, `TF` e `RobotModel`. No display `Map`, use `Reliable` e
`Transient Local`. Valide:

```bash
ros2 topic hz /map
ros2 topic hz /lidar_plugin/out
ros2 run tf2_ros tf2_echo map base_link
```

A cadeia esperada é `map -> odom -> base_link -> lidar_link`.

Se o RViz apresentar `No map received`, confira em `Map`:

```text
Topic: /map
Reliability Policy: Reliable
Durability Policy: Transient Local
```

Também confirme que `/map` possui um publisher e que o RViz aparece como
subscriber:

```bash
ros2 topic info /map -v
ros2 topic echo /map --once
```

### Comparação do Exercício 2

Repita a ordem acima para três casos:

1. `sensor_noise:=false`, `odom_noise:=false`: Lidar e odometria ground truth;
2. `sensor_noise:=true`, `odom_noise:=false`: Lidar ruidoso e odometria ground truth;
3. `sensor_noise:=true`, `odom_noise:=true`: Lidar e odometria relativos ruidosos.

O caso 1 deve produzir o mapa mais limpo. No caso 2, as paredes podem ficar
mais espessas ou irregulares. No caso 3, o erro de dead reckoning aumenta, mas
o scan matching tenta corrigi-lo. O mapa e a transformação `map -> odom` são
os critérios de comparação.

Salve o mapa:

```bash
ros2 run nav2_map_server map_saver_cli -f ~/mapa_slam
```

## 5. Robô sequestrado

Use o caso 3 com o mapa parcialmente construído:

1. Pause o Gazebo;
2. selecione `meu_robo`;
3. use a ferramenta de translação para movê-lo para o outro lado do mapa;
4. retome a simulação;
5. observe `/map`, `/lidar_plugin/out` e `map -> odom`.

A recuperação é bem-sucedida se o SLAM corrigir `map -> odom` e posicionar o
robô de forma coerente com as paredes e obstáculos do mapa, sem GPS.

## Fala sugerida — aproximadamente 3 minutos

> Neste experimento, todas as estimativas são relativas: não utilizamos GPS nem
> outra fonte de posição absoluta. O robô utiliza odometria de dead reckoning,
> baseada nos encoders e nos sensores disponíveis, enquanto o `slam_toolbox`
> combina a odometria com as leituras do Lidar 2D.
>
> Primeiro adicionamos ruído gaussiano às medições do Lidar. O sensor publica
> `LaserScan` e o ruído é opcional, permitindo comparar medições ideais e
> medições mais próximas de um sensor real.
>
> Depois configuramos o `slam_toolbox` para fazer SLAM 2D no cenário com paredes
> e obstáculos distribuídos. O robô é movimentado autonomamente pelo
> `explorer_node`, que usa o Lidar para avançar e desviar dos obstáculos. O
> `slam_toolbox` recebe o Lidar e a odometria relativa, constrói `/map` e
> publica a transformação `map` para `odom`.
>
> A comparação possui três situações. Na primeira, usamos tudo ground truth:
> Lidar sem ruído e odometria ground truth. Esse é o caso de referência e deve
> produzir o mapa mais limpo. Na segunda, adicionamos ruído ao Lidar, mas
> mantemos a odometria ground truth. Nesse caso, as paredes podem ficar mais
> espessas ou irregulares, mas o movimento ainda é conhecido com precisão. Na
> terceira situação, adicionamos ruído ao Lidar e também aos incrementos da
> odometria. Esse é o caso mais difícil, pois há ruído de medição e acúmulo de
> erro de dead reckoning. O scan matching do SLAM tenta reduzir esse erro
> comparando as leituras atuais com o mapa construído.
>
> Por fim, realizamos o experimento do robô sequestrado usando o terceiro caso.
> Com o mapa já construído, pausamos o Gazebo, selecionamos o robô no modo de
> translação e o movemos para o outro lado do mapa. Ao retomar a simulação,
> verificamos se o `slam_toolbox` consegue corrigir `map` para `odom` e
> recuperar uma pose coerente com as paredes e obstáculos já mapeados.
> Consideramos a recuperação bem-sucedida somente se essa correção for visível
> no TF e no RViz2. O fato de `/map` continuar sendo publicado, sozinho, não
> prova que a localização foi recuperada.

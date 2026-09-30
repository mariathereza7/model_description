import math
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist, PoseStamped
from nav_msgs.msg import Odometry

class TrajectoryNode(Node):
    def __init__(self):
        super().__init__('trajectory_node')
        
        self.declare_parameter('A', 1.0)
        self.declare_parameter('B', 2.0)
        self.declare_parameter('omega', 0.5)
        self.declare_parameter('k_ff', 1.0) # 0.0 para malha fechada pura, 1.0 para feedforward
        self.declare_parameter('open_loop', False) # True para malha aberta pura

        self.A = self.get_parameter('A').value
        self.B = self.get_parameter('B').value
        self.W = self.get_parameter('omega').value
        self.k_ff = self.get_parameter('k_ff').value
        self.open_loop = self.get_parameter('open_loop').value

        self.sub_odom = self.create_subscription(Odometry, '/odom', self.odom_cb, 10)
        self.pub_cmd = self.create_publisher(Twist, '/cmd_vel', 10)
        self.pub_ref_pose = self.create_publisher(PoseStamped, '/ref_pose', 10)

        self.t = 0.0
        self.dt = 0.05 # 20 Hz
        self.timer = self.create_timer(self.dt, self.loop)

    def odom_cb(self, msg):
        self.x = msg.pose.pose.position.x
        self.y = msg.pose.pose.position.y
        q = msg.pose.pose.orientation
        self.theta = math.atan2(2*(q.w*q.z + q.x*q.y), 1 - 2*(q.y**2 + q.z**2))

    def loop(self):
        # 1. Posições e derivadas desejadas em t
        xd = self.A * math.sin(self.W * self.t)
        yd = (self.B / 2.0) * math.sin(2 * self.W * self.t)
        
        dxd = self.A * self.W * math.cos(self.W * self.t)
        dyd = self.B * self.W * math.cos(2 * self.W * self.t)
        
        ddxd = - self.A * (self.W**2) * math.sin(self.W * self.t)
        ddyd = -2 * self.B * (self.W**2) * math.sin(2 * self.W * self.t)

        thetad = math.atan2(dyd, dxd)
        
        # 2. Termos Feedforward (Malha Aberta)
        v_ff = math.sqrt(dxd**2 + dyd**2)
        w_ff = (ddyd * dxd - ddxd * dyd) / (dxd**2 + dyd**2 + 1e-6)

        if self.open_loop:
            v_cmd = v_ff
            w_cmd = w_ff
        else:
            # 3. Realimentação (PID / Proporcional nos erros no referencial local)[cite: 7]
            ex_i = xd - self.x
            ey_i = yd - self.y
            etheta = math.atan2(math.sin(thetad - self.theta), math.cos(thetad - self.theta))

            ex_b = math.cos(self.theta)*ex_i + math.sin(self.theta)*ey_i
            ey_b = -math.sin(self.theta)*ex_i + math.cos(self.theta)*ey_i

            # v_ref = K_ff * v_ff + PID(ex_b)[cite: 7, 8]
            # w_ref = K_ff * w_ff + PID(ey_b, etheta)[cite: 7, 8]
            v_cmd = self.k_ff * v_ff + 1.0 * ex_b
            w_cmd = self.k_ff * w_ff + (1.5 * ey_b + 2.0 * etheta)

        cmd = Twist()
        cmd.linear.x = v_cmd
        cmd.angular.z = w_cmd
        self.pub_cmd.publish(cmd)

        self.t += self.dt
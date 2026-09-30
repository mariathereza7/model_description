import math
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist, PoseStamped
from nav_msgs.msg import Odometry

class PoseControlNode(Node):
    def __init__(self):
        super().__init__('pose_control_node')
        
        # Declarar e carregar parâmetros
        self.declare_parameter('kp_x', 1.0)
        self.declare_parameter('kp_y', 1.0)
        self.declare_parameter('kp_theta', 2.0)
        
        self.kp_x = self.get_parameter('kp_x').value
        self.kp_y = self.get_parameter('kp_y').value
        self.kp_theta = self.get_parameter('kp_theta').value
        
        # Inscrições e Publicações
        self.sub_odom = self.create_subscription(Odometry, '/odom', self.odom_callback, 10)
        self.sub_goal = self.create_subscription(PoseStamped, '/goal_pose', self.goal_callback, 10)
        self.pub_cmd = self.create_publisher(Twist, '/cmd_vel', 10)
        
        self.current_x = 0.0
        self.current_y = 0.0
        self.current_theta = 0.0
        
        self.goal_x = None
        self.goal_y = None
        self.goal_theta = None
        
        self.timer = self.create_timer(0.05, self.control_loop) # 20 Hz

    def odom_callback(self, msg):
        self.current_x = msg.pose.pose.position.x
        self.current_y = msg.pose.pose.position.y
        
        # Conversão de Quatérnio para Yaw (Theta)
        q = msg.pose.pose.orientation
        siny_cosp = 2 * (q.w * q.z + q.x * q.y)
        cosy_cosp = 1 - 2 * (q.y * q.y + q.z * q.z)
        self.current_theta = math.atan2(siny_cosp, cosy_cosp)

    def goal_callback(self, msg):
        self.goal_x = msg.pose.position.x
        self.goal_y = msg.pose.position.y
        q = msg.pose.orientation
        siny_cosp = 2 * (q.w * q.z + q.x * q.y)
        cosy_cosp = 1 - 2 * (q.y * q.y + q.z * q.z)
        self.goal_theta = math.atan2(siny_cosp, cosy_cosp)

    def control_loop(self):
        if self.goal_x is None:
            return

        # Erro em relação ao referencial Global {I}
        ex_i = self.goal_x - self.current_x
        ey_i = self.goal_y - self.current_y
        etheta = self.goal_theta - self.current_theta
        etheta = math.atan2(math.sin(etheta), math.cos(etheta)) # Normalização [-pi, pi]

        # Mudança de Base para o Referencial do Robô {B} (R^-1 * e_I)
        c_th = math.cos(self.current_theta)
        s_th = math.sin(self.current_theta)
        
        ex_b =  c_th * ex_i + s_th * ey_i
        ey_b = -s_th * ex_i + c_th * ey_i

        # Sinal de Controle PID (Apenas Proporcional P neste exemplo)
        v = self.kp_x * ex_b
        w = self.kp_y * ey_b + self.kp_theta * etheta

        cmd = Twist()
        cmd.linear.x = v
        cmd.angular.z = w
        self.pub_cmd.publish(cmd)

def main(args=None):
    rclpy.init(args=args)
    node = PoseControlNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()
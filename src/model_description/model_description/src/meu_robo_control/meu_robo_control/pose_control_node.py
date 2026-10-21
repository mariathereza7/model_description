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
        
        self.declare_parameter('tolerance', 0.05)
        self.declare_parameter('yaw_tolerance', 0.05)
        self.declare_parameter('max_linear_speed', 0.4)
        self.declare_parameter('max_angular_speed', 1.5)
        self.tolerance = self.get_parameter('tolerance').value
        self.yaw_tolerance = self.get_parameter('yaw_tolerance').value
        self.max_linear_speed = self.get_parameter('max_linear_speed').value
        self.max_angular_speed = self.get_parameter('max_angular_speed').value
        self.have_odom = False

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
        self.have_odom = True
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
        if self.goal_x is None or not self.have_odom:
            return

        dx = self.goal_x - self.current_x
        dy = self.goal_y - self.current_y
        distance = math.hypot(dx, dy)
        cmd = Twist()
        if distance > self.tolerance:
            heading_error = math.atan2(dy, dx) - self.current_theta
            heading_error = math.atan2(math.sin(heading_error), math.cos(heading_error))
            # Face the target before driving; final yaw must not cancel steering.
            if abs(heading_error) < math.pi / 4:
                cmd.linear.x = min(self.max_linear_speed, self.kp_x * distance) * math.cos(heading_error)
            cmd.angular.z = max(-self.max_angular_speed,
                                min(self.max_angular_speed, self.kp_y * heading_error))
        else:
            yaw_error = self.goal_theta - self.current_theta
            yaw_error = math.atan2(math.sin(yaw_error), math.cos(yaw_error))
            if abs(yaw_error) > self.yaw_tolerance:
                cmd.angular.z = max(-self.max_angular_speed,
                                    min(self.max_angular_speed, self.kp_theta * yaw_error))
        self.pub_cmd.publish(cmd)

def main(args=None):
    rclpy.init(args=args)
    node = PoseControlNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()
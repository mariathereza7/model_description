import math
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist, PoseStamped
from nav_msgs.msg import Odometry

from meu_robo_control.pid_controller import PID

class PoseControlNode(Node):
    def __init__(self):
        super().__init__('pose_control_node')
        
        # Declarar e carregar parâmetros
        for name, default in (
                ('kp_x', 1.0), ('ki_x', 0.0), ('kd_x', 0.0),
                ('kp_y', 1.0), ('ki_y', 0.0), ('kd_y', 0.0),
                ('kp_theta', 2.0), ('ki_theta', 0.0), ('kd_theta', 0.0)):
            self.declare_parameter(name, default)
        
        self.declare_parameter('tolerance', 0.05)
        self.declare_parameter('yaw_tolerance', 0.05)
        self.declare_parameter('max_linear_speed', 0.4)
        self.declare_parameter('max_angular_speed', 1.5)
        self.tolerance = self.get_parameter('tolerance').value
        self.yaw_tolerance = self.get_parameter('yaw_tolerance').value
        self.max_linear_speed = self.get_parameter('max_linear_speed').value
        self.max_angular_speed = self.get_parameter('max_angular_speed').value
        self.have_odom = False

        self.pid_x = PID(self.get_parameter('kp_x').value, self.get_parameter('ki_x').value,
                         self.get_parameter('kd_x').value,
                         -self.max_linear_speed, self.max_linear_speed)
        self.pid_y = PID(self.get_parameter('kp_y').value, self.get_parameter('ki_y').value,
                         self.get_parameter('kd_y').value,
                         -self.max_angular_speed, self.max_angular_speed)
        self.pid_theta = PID(self.get_parameter('kp_theta').value,
                             self.get_parameter('ki_theta').value,
                             self.get_parameter('kd_theta').value,
                             -self.max_angular_speed, self.max_angular_speed)
        
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
        self.last_goal = None
        
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
        goal = (self.goal_x, self.goal_y, self.goal_theta)
        if self.last_goal is None or goal != self.last_goal:
            self.pid_x.reset()
            self.pid_y.reset()
            self.pid_theta.reset()
            self.last_goal = goal

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
            # PID on distance and heading; reducing linear speed while turning
            # prevents overshoot and keeps the continuous controller stable.
            cmd.linear.x = self.pid_x.update(distance, 0.05) * max(0.0, math.cos(heading_error))
            cmd.angular.z = self.pid_y.update(heading_error, 0.05)
        else:
            yaw_error = self.goal_theta - self.current_theta
            yaw_error = math.atan2(math.sin(yaw_error), math.cos(yaw_error))
            if abs(yaw_error) > self.yaw_tolerance:
                cmd.angular.z = self.pid_theta.update(yaw_error, 0.05)
            else:
                self.pid_theta.reset()
        self.pub_cmd.publish(cmd)

def main(args=None):
    rclpy.init(args=args)
    node = PoseControlNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()
